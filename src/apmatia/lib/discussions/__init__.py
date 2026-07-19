from __future__ import annotations

import base64
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from persistence import SQLiteStore
except ModuleNotFoundError:
    from apmatia.lib.persistence.persistence import SQLiteStore

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.app_config import get_config_value
from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.core.user_management_runtime import get_group_manager
from apmatia.core.wiki_management_runtime import get_wiki_manager
from apmatia.core.tool_management_runtime import get_tool_manager
from apmatia.lib.agent_management.agent_prompt import compile_agent_system_prompt, default_agent_prompt
from apmatia.lib.agent_management.models import Agent
from apmatia.lib.apmatia_core.models import ApmatiaObject, utc_now
from apmatia.lib.model_management.models import LLM

from apmatia.lib.discussions.discussion_templates import DISCUSSION_CHAT_TEMPLATE, build_chat_messages
from apmatia.lib.discussions.group_chat import (
    GROUP_CHAT_MODES,
    GroupChatParticipant,
    build_group_chat_plan,
    normalize_group_chat_mode,
)
from apmatia.lib.discussions.prompt_llm import prompt_llm
from apmatia.lib.discussions.tool_calls import (
    extend_system_prompt_with_tools,
    format_tool_result_message,
    parse_tool_calls,
    strip_tool_calls,
    ToolCallStreamFilter,
)
from apmatia.lib.llama_server.log_parser import parse_llama_server_log_file, parse_llama_server_log_turns
from apmatia.lib.tool_management.models import ToolCall


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
DISCUSSIONS_DIR = DATA_DIR / "discussions"
DISCUSSIONS_DB = DATA_DIR / "discussions.db"
TRASH_RETENTION_DAYS = 90
MAX_PROMPT_ATTACHMENT_BYTES = 10 * 1024 * 1024
_UNSET = object()
_MESSAGE_ROLE_RE = re.compile(r"^(User|Assistant|Agent)(?:\s*\((?P<speaker>[^)]+)\))?:\s?")
_MESSAGE_METADATA_RE = re.compile(r"^<!--\s*apmatia-metadata:\s*(?P<payload>.+?)\s*-->$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_int(value: object, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _new_discussion_id() -> str:
    return f"ID{uuid.uuid4().hex[:8]}"


def _normalize_agent_mode(value: object | None) -> str:
    candidate = "discussion" if value is None else str(value).strip().lower()
    if candidate in {"discussion", "agentic"}:
        return candidate
    return "discussion"


@dataclass(slots=True)
class DiscussionSnapshot:
    discussion_id: str
    is_streaming: bool
    last_error: str | None
    agent_mode: str
    chat_mode: str
    chat_pause_seconds: float | None
    chat_is_paused: bool
    chat_turn_index: int
    chat_coordinator_agent_id: int | None
    system_prompt: str
    content: str
    messages: list[dict[str, str]]
    activity: dict[str, Any] | None
    llama_server_status: dict[str, Any] | None


@dataclass(slots=True)
class Discussion(ApmatiaObject):
    title: str = "Untitled Discussion"
    group_id: int | None = None
    visibility: str = "private"
    folder_id: int | None = None
    focused_wiki_id: str | None = None
    participant_agent_ids: list[int] | None = None
    agent_mode: str = "discussion"
    chat_mode: str = "round_robin"
    chat_pause_seconds: float | None = None
    chat_is_paused: bool = False
    chat_turn_index: int = 0
    chat_coordinator_agent_id: int | None = None
    system_prompt: str = ""
    last_error: str | None = None
    deleted_at: str | None = None
    purge_after: str | None = None

    @property
    def discussion_id(self) -> str:
        return "" if self.id is None else str(self.id)

    def __post_init__(self) -> None:
        super().__post_init__()
        raw_ids = self.participant_agent_ids or []
        self.participant_agent_ids = []
        seen_ids: set[int] = set()
        for raw_id in raw_ids:
            agent_id = safe_int(raw_id, default=None)
            if agent_id is not None and agent_id not in seen_ids:
                self.participant_agent_ids.append(agent_id)
                seen_ids.add(agent_id)
        self.agent_mode = _normalize_agent_mode(self.agent_mode)
        self.chat_mode = normalize_group_chat_mode(self.chat_mode)
        self.chat_pause_seconds = None if self.chat_pause_seconds is None else float(self.chat_pause_seconds)
        self.chat_is_paused = bool(self.chat_is_paused)
        self.chat_turn_index = max(0, safe_int(self.chat_turn_index, default=0) or 0)
        self.chat_coordinator_agent_id = safe_int(self.chat_coordinator_agent_id, default=None)


@dataclass(slots=True)
class _AssistantTranscriptWriter:
    state: "DiscussionState"
    discussion_id: str
    role: str = "Assistant"
    speaker_name: str | None = None
    started: bool = False
    visible_char_count: int = 0

    def append(self, text: str) -> None:
        chunk = str(text or "")
        if not chunk:
            return
        label = self.role
        if self.speaker_name:
            label = f"{self.role} ({self.speaker_name})"
        prefix = f"\n\n{label}: " if not self.started else ""
        self.state._append_text(self.discussion_id, f"{prefix}{chunk}")
        self.started = True
        self.visible_char_count += len(chunk)

    def append_metadata(self, metadata: dict[str, Any] | None) -> None:
        payload = dict(metadata or {})
        if not payload:
            return
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.state._append_text(self.discussion_id, f"\n\n<!-- apmatia-metadata: {serialized} -->")


class DiscussionState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: SQLiteStore | None = None
        self._threads: dict[str, threading.Thread] = {}
        self._streaming: set[str] = set()
        self._stop_events: dict[str, threading.Event] = {}
        self._activity: dict[str, dict[str, Any]] = {}
        self._pending_prompt_attachments: dict[str, list[dict[str, Any]]] = {}

    @property
    def _ensure_store(self) -> SQLiteStore:
        if self._store is None:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            DISCUSSIONS_DIR.mkdir(parents=True, exist_ok=True)
            self._store = SQLiteStore(DISCUSSIONS_DB)
        return self._store

    def _discussion_path(self, discussion_id: str) -> Path:
        return DISCUSSIONS_DIR / f"{discussion_id}.txt"

    def _discussion_attachment_directory(self, discussion_id: str) -> Path:
        return DISCUSSIONS_DIR / discussion_id / "attachments"

    def _store_prompt_attachments(
        self,
        discussion_id: str,
        attachments: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        if not attachments:
            return []

        stored_attachments: list[dict[str, Any]] = []
        attachment_dir = self._discussion_attachment_directory(discussion_id)
        attachment_dir.mkdir(parents=True, exist_ok=True)

        for index, attachment in enumerate(attachments):
            if not isinstance(attachment, dict):
                raise ValueError("Invalid attachment payload.")

            mime_type = str(attachment.get("mime_type") or "").strip().lower()
            if not mime_type.startswith("image/"):
                raise ValueError("Only image attachments are supported.")

            data_base64 = str(attachment.get("data_base64") or "").strip()
            if not data_base64:
                raise ValueError("Attachment data cannot be empty.")
            try:
                binary = base64.b64decode(data_base64, validate=True)
            except ValueError as error:
                raise ValueError("Attachment data is not valid base64.") from error
            if len(binary) > MAX_PROMPT_ATTACHMENT_BYTES:
                raise ValueError("Attachment exceeds the maximum supported size.")

            filename = str(attachment.get("filename") or f"attachment-{index + 1}").strip()
            if not filename:
                filename = f"attachment-{index + 1}"

            extension = mime_type.split("/", 1)[-1] or "bin"
            stored_name = f"{uuid.uuid4().hex}.{extension}"
            stored_path = attachment_dir / stored_name
            stored_path.write_bytes(binary)

            stored_attachments.append(
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "path": f"attachments/{stored_name}",
                    "size_bytes": len(binary),
                }
            )

        return stored_attachments

    def _attachment_data_url(self, discussion_id: str, attachment: dict[str, Any]) -> str | None:
        data_url = str(attachment.get("data_url") or "").strip()
        if data_url:
            return data_url

        mime_type = str(attachment.get("mime_type") or "").strip()
        if not mime_type:
            return None

        path_value = str(attachment.get("path") or "").strip()
        if not path_value:
            return None

        stored_path = self._discussion_attachment_directory(discussion_id) / Path(path_value).name
        if not stored_path.exists():
            return None

        binary = stored_path.read_bytes()
        encoded = base64.b64encode(binary).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _attachment_content_parts(self, discussion_id: str, attachment: dict[str, Any]) -> dict[str, Any] | None:
        data_url = self._attachment_data_url(discussion_id, attachment)
        if not data_url:
            return None
        return {"type": "image_url", "image_url": {"url": data_url}}

    def _hydrate_message_attachments(
        self,
        discussion_id: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            return message

        raw_attachments = metadata.get("attachments")
        if not isinstance(raw_attachments, list) or not raw_attachments:
            return message

        hydrated_attachments: list[dict[str, Any]] = []
        for attachment in raw_attachments:
            if not isinstance(attachment, dict):
                continue
            updated_attachment = dict(attachment)
            data_url = self._attachment_data_url(discussion_id, updated_attachment)
            if data_url:
                updated_attachment["data_url"] = data_url
            hydrated_attachments.append(updated_attachment)

        if hydrated_attachments:
            updated_message = dict(message)
            hydrated_metadata = dict(metadata)
            hydrated_metadata["attachments"] = hydrated_attachments
            updated_message["metadata"] = hydrated_metadata
            return updated_message
        return message

    def _get_pending_prompt_attachments(self, discussion_id: str) -> list[dict[str, Any]]:
        with self._lock:
            attachments = self._pending_prompt_attachments.pop(discussion_id, [])
            return [dict(attachment) for attachment in attachments]

    def _chat_messages_include_images(self, chat_messages: list[dict[str, Any]]) -> bool:
        for message in chat_messages:
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        return True
            elif isinstance(content, dict) and content.get("type") == "image_url":
                return True
        return False

    def _chat_message_text_length(self, message: dict[str, Any]) -> int:
        content = message.get("content")
        if isinstance(content, str):
            return len(content)
        if isinstance(content, list):
            return sum(len(str(part.get("text", ""))) for part in content if isinstance(part, dict))
        if isinstance(content, dict):
            return len(str(content.get("text", "")))
        return 0

    def _discussion_from_row(self, row: dict | None) -> Discussion | None:
        if row is None:
            return None
        discussion_id = str(row.get("discussion_id") or row.get("id") or "").strip()
        if not discussion_id:
            return None
        group_id = safe_int(row.get("group_id"), default=None)
        visibility = str(row.get("visibility") or ("group" if group_id is not None else "private"))
        return Discussion(
            id=discussion_id,
            owner_user_id=safe_int(row.get("owner_user_id"), default=None),
            owner_group_id=safe_int(row.get("owner_group_id"), default=None),
            mode=safe_int(row.get("mode"), default=0) or 0,
            created_at=parse_iso_datetime(row.get("created_at")) or utc_now(),
            updated_at=parse_iso_datetime(row.get("updated_at")) or utc_now(),
            title=str(row.get("title", "Untitled Discussion")),
            group_id=group_id,
            visibility=visibility,
            folder_id=safe_int(row.get("folder_id"), default=None),
            focused_wiki_id=None if row.get("focused_wiki_id") is None else str(row.get("focused_wiki_id")),
            participant_agent_ids=list(row.get("participant_agent_ids") or []),
            agent_mode=_normalize_agent_mode(row.get("agent_mode")),
            chat_mode=str(row.get("chat_mode") or "round_robin"),
            chat_pause_seconds=row.get("chat_pause_seconds"),
            chat_is_paused=bool(row.get("chat_is_paused", False)),
            chat_turn_index=safe_int(row.get("chat_turn_index"), default=0) or 0,
            chat_coordinator_agent_id=safe_int(row.get("chat_coordinator_agent_id"), default=None),
            system_prompt=str(row.get("system_prompt", "")),
            last_error=None if row.get("last_error") is None else str(row.get("last_error")),
            deleted_at=None if row.get("deleted_at") is None else str(row.get("deleted_at")),
            purge_after=None if row.get("purge_after") is None else str(row.get("purge_after")),
        )

    def _discussion_to_store_payload(self, discussion: Discussion) -> dict:
        return {
            "discussion_id": discussion.discussion_id,
            "owner_user_id": discussion.owner_user_id,
            "owner_group_id": discussion.owner_group_id,
            "mode": discussion.mode,
            "title": discussion.title,
            "group_id": discussion.group_id,
            "visibility": discussion.visibility,
            "folder_id": discussion.folder_id,
            "focused_wiki_id": discussion.focused_wiki_id,
            "participant_agent_ids": list(discussion.participant_agent_ids),
            "agent_mode": discussion.agent_mode,
            "chat_mode": discussion.chat_mode,
            "chat_pause_seconds": discussion.chat_pause_seconds,
            "chat_is_paused": discussion.chat_is_paused,
            "chat_turn_index": discussion.chat_turn_index,
            "chat_coordinator_agent_id": discussion.chat_coordinator_agent_id,
            "system_prompt": discussion.system_prompt,
            "last_error": discussion.last_error,
            "deleted_at": discussion.deleted_at,
            "purge_after": discussion.purge_after,
            "created_at": discussion.created_at.isoformat(),
            "updated_at": discussion.updated_at.isoformat(),
        }

    def _discussion_to_public_dict(self, discussion: Discussion) -> dict:
        return {
            "discussion_id": discussion.discussion_id,
            "title": discussion.title,
            "owner_user_id": discussion.owner_user_id,
            "owner_group_id": discussion.owner_group_id,
            "mode": discussion.mode,
            "group_id": discussion.group_id,
            "visibility": discussion.visibility,
            "folder_id": discussion.folder_id,
            "focused_wiki_id": discussion.focused_wiki_id,
            "participant_agent_ids": list(discussion.participant_agent_ids),
            "agent_mode": discussion.agent_mode,
            "chat_mode": discussion.chat_mode,
            "chat_pause_seconds": discussion.chat_pause_seconds,
            "chat_is_paused": discussion.chat_is_paused,
            "chat_turn_index": discussion.chat_turn_index,
            "chat_coordinator_agent_id": discussion.chat_coordinator_agent_id,
            "system_prompt": discussion.system_prompt,
            "last_error": discussion.last_error,
            "deleted_at": discussion.deleted_at,
            "purge_after": discussion.purge_after,
            "created_at": discussion.created_at.isoformat(),
            "updated_at": discussion.updated_at.isoformat(),
        }

    def _parse_messages(self, content: str) -> list[dict[str, str]]:
        lines = str(content or "").split("\n")
        messages: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        for line in lines:
            match = _MESSAGE_ROLE_RE.match(line)
            if match:
                if current is not None:
                    messages.append(current)
                role = match.group(1)
                speaker_name = match.group("speaker")
                rest = line[match.end() :]
                current = {"role": role, "text": rest.lstrip(), "metadata": {}}
                if speaker_name:
                    current["speaker_name"] = speaker_name.strip()
                continue

            match = _MESSAGE_METADATA_RE.match(line.strip())
            if match and current is not None:
                payload = match.group("payload").strip()
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    parsed = {}
                if isinstance(parsed, dict):
                    current["metadata"] = parsed
                continue

            if current is None and not line.strip():
                continue
            if current is None:
                current = {"role": "Assistant", "text": "", "metadata": {}}
            separator = "\n" if current["text"] else ""
            current["text"] = f"{current['text']}{separator}{line}"

        if current is not None:
            messages.append(current)

        cleaned: list[dict[str, Any]] = []
        for message in messages:
            text = str(message.get("text", "")).rstrip()
            if not text:
                continue
            cleaned_message = {
                "role": str(message.get("role", "Assistant")),
                "text": text,
            }
            speaker_name = str(message.get("speaker_name", "")).strip()
            if speaker_name:
                cleaned_message["speaker_name"] = speaker_name
            metadata = message.get("metadata")
            if isinstance(metadata, dict) and metadata:
                cleaned_message["metadata"] = dict(metadata)
            cleaned.append(cleaned_message)
        return cleaned

    def _append_text(self, discussion_id: str, text: str) -> None:
        path = self._discussion_path(discussion_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
            file.flush()

    def _append_assistant_prompt(self, discussion_id: str, speaker_name: str | None = None) -> None:
        prefix = "Assistant:"
        if speaker_name:
            prefix = f"Agent ({speaker_name}):"
        self._append_text(discussion_id, f"{prefix} ")

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        for message in messages:
            role = str(message.get("role", "Assistant")).strip() or "Assistant"
            text = str(message.get("text", "")).rstrip()
            if not text:
                continue
            prefix = f"{role}: "
            block = f"{prefix}{text}"
            metadata = message.get("metadata")
            if isinstance(metadata, dict) and metadata:
                block = (
                    f"{block}\n\n"
                    f"<!-- apmatia-metadata: {json.dumps(metadata, ensure_ascii=False, sort_keys=True)} -->"
                )
            blocks.append(block)
        return "\n\n".join(blocks).rstrip() + ("\n" if blocks else "")

    def _get_agent(self, agent_id: int) -> Agent | None:
        return get_agent_manager().get_agent(agent_id)

    def _get_llm_config(self, config_id: int) -> LLM | None:
        for config in get_llm_config_manager().list_configs():
            if config.id == config_id:
                return config
        return None

    def _resolve_agent_llm_config(self, agent_id: int) -> LLM:
        agent = self._get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        for candidate_id in (agent.active_model_id, agent.default_model_id):
            if candidate_id is None:
                continue
            llm_config = self._get_llm_config(int(candidate_id))
            if llm_config is not None:
                return llm_config

        raise ValueError(f"No usable model configured for agent: {agent_id}")

    def _llm_config_summary(self, llm_config: LLM | None) -> dict[str, Any]:
        if llm_config is None:
            return {}
        return {
            "model_id": getattr(llm_config, "id", None),
            "model_name": (
                getattr(llm_config, "user_alias", "")
                or getattr(llm_config, "provider_name", "")
                or getattr(llm_config, "model_name", "")
            ),
            "provider_name": getattr(llm_config, "provider_name", ""),
            "backend": getattr(llm_config, "backend", ""),
            "model_url": getattr(llm_config, "model_url", ""),
        }

    def _prompt_activity_summary(
        self,
        *,
        discussion_id: str,
        agent: Agent,
        speaker_name: str,
        llm_config: LLM | None,
        chat_messages: list[dict[str, Any]],
        prompt: str,
    ) -> dict[str, Any]:
        system_prompt = ""
        if chat_messages and isinstance(chat_messages[0], dict):
            system_prompt = str(chat_messages[0].get("content", ""))
        prompt_text = str(prompt or "")
        visible_messages = max(0, len(chat_messages) - 1)
        summary = {
            "stage": "generating",
            "agent_id": getattr(agent, "id", None),
            "agent_name": str(getattr(agent, "name", "") or "Agent"),
            "speaker_name": speaker_name,
            "model": self._llm_config_summary(llm_config),
            "prompt": {
                "messages": visible_messages,
                "prompt_characters": len(prompt_text),
                "system_characters": len(system_prompt),
                "transcript_characters": sum(self._chat_message_text_length(message) for message in chat_messages),
            },
            "stream": {
                "chunk_count": 0,
                "visible_characters": 0,
            },
            "tool": None,
            "stats": {},
        }
        return summary

    def _resolve_agent_system_prompt(self, agent_id: int) -> str:
        agent = self._get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        prompt = default_agent_prompt()
        if agent.prompt_id is not None:
            agent_manager = get_agent_manager()
            resolved = agent_manager.get_prompt(agent.prompt_id)
            if resolved is not None:
                prompt = resolved
        return compile_agent_system_prompt(agent.name, prompt)

    def _list_tools_available_to_agent(self, agent_id: int) -> list[Any]:
        return get_tool_manager().list_tools_available_to_agent(agent_id)

    def _call_llm(
        self,
        *,
        discussion_id: str,
        prompt: str,
        chat_messages: list[dict[str, Any]],
        llm_config: LLM | None,
        stop_event: threading.Event | None,
        on_chunk: Any | None = None,
        on_event: Any | None = None,
    ) -> str:
        backend_name = str(getattr(llm_config, "backend", "") or "openai_compatible").strip().lower()
        if self._chat_messages_include_images(chat_messages) and backend_name not in {
            "openai",
            "openai_compatible",
            "openai-compatible",
        }:
            raise ValueError("The selected model backend does not support image attachments.")

        return prompt_llm(
            prompt=prompt,
            output_dir=str(DISCUSSIONS_DIR),
            prompt_id=f"{discussion_id}-{uuid.uuid4().hex}",
            append_existing=False,
            context=None,
            request_metadata={
                "chat_template": DISCUSSION_CHAT_TEMPLATE,
                "chat_messages": chat_messages,
                "add_generation_prompt": True,
            },
            llm_config=llm_config,
            stop_event=stop_event,
            on_chunk=on_chunk,
            on_event=on_event,
        )

    def _append_message(
        self,
        discussion_id: str,
        role: str,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        clean_text = str(text).strip()
        if not clean_text:
            return
        path = self._discussion_path(discussion_id)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        prefix = "\n\n" if existing.rstrip() else ""
        payload = f"{prefix}{role}: {clean_text}"
        if isinstance(metadata, dict) and metadata:
            payload = (
                f"{payload}\n\n"
                f"<!-- apmatia-metadata: {json.dumps(metadata, ensure_ascii=False, sort_keys=True)} -->"
            )
        self._append_text(discussion_id, payload)

    def _append_group_agent_message(
        self,
        discussion_id: str,
        *,
        speaker_name: str,
        text: str,
    ) -> None:
        clean_text = str(text).strip()
        if not clean_text:
            return
        path = self._discussion_path(discussion_id)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        prefix = "\n\n" if existing.rstrip() else ""
        self._append_text(discussion_id, f"{prefix}Agent ({speaker_name}): {clean_text}")

    def _new_assistant_stream_writer(
        self,
        discussion_id: str,
        *,
        role: str = "Assistant",
        speaker_name: str | None = None,
    ) -> "_AssistantTranscriptWriter":
        return _AssistantTranscriptWriter(
            state=self,
            discussion_id=discussion_id,
            role=role,
            speaker_name=speaker_name,
        )

    def _set_activity(self, discussion_id: str, **updates: Any) -> None:
        with self._lock:
            current = dict(self._activity.get(discussion_id) or {})
            current.update(updates)
            current["updated_at"] = utc_now_iso()
            self._activity[discussion_id] = current

    def _clear_activity(self, discussion_id: str) -> None:
        with self._lock:
            self._activity.pop(discussion_id, None)

    def _get_activity(self, discussion_id: str) -> dict[str, Any] | None:
        with self._lock:
            activity = self._activity.get(discussion_id)
            return None if activity is None else dict(activity)

    def _resolve_llama_server_log_source(self) -> str | None:
        configured_log_dir = str(
            get_config_value("llama_server", "log_dir", default=None) or ""
        ).strip()
        if configured_log_dir:
            return configured_log_dir
        return (
            os.getenv("APMATIA_LLAMA_SERVER_LOG_FILE")
            or os.getenv("LLAMA_LOG_FILE")
            or os.getenv("APMATIA_LLAMA_SERVER_LOG_DIR")
            or os.getenv("LLAMA_LOG_DIR")
        )

    def _llama_server_status(self) -> dict[str, Any] | None:
        log_source = self._resolve_llama_server_log_source()
        if not log_source:
            return None
        status = parse_llama_server_log_file(log_source)
        return None if status is None else status.to_dict()

    def _llama_server_turns(self) -> list[dict[str, Any]]:
        log_source = self._resolve_llama_server_log_source()
        if not log_source:
            return []
        path = Path(log_source).expanduser()
        if path.is_dir():
            candidates = [
                candidate
                for candidate in path.iterdir()
                if candidate.is_file() and not candidate.name.startswith(".")
            ]
            if not candidates:
                return []
            path = max(candidates, key=lambda candidate: (candidate.stat().st_mtime, candidate.name))
        if not path.exists():
            return []
        turns = parse_llama_server_log_turns(path.read_text(encoding="utf-8", errors="replace"))
        return [turn.to_dict() for turn in turns]

    def _llama_server_status_has_renderable_metrics(self, status: dict[str, Any] | None) -> bool:
        if not isinstance(status, dict):
            return False
        return any(
            status.get(key) is not None
            for key in (
                "prompt_processing_progress",
                "prompt_processing_n_tokens",
                "prompt_tokens_total",
                "prompt_eval",
                "eval",
                "total_time_ms",
                "total_tokens",
            )
        )

    def _execute_tool_calls(
        self,
        *,
        agent_id: int,
        discussion_id: str,
        tool_calls: list[Any],
    ) -> list[dict[str, str]]:
        if not tool_calls:
            return []

        tool_manager = get_tool_manager()
        available_tools = {
            str(tool.name): tool
            for tool in tool_manager.list_tools_available_to_agent(agent_id)
            if getattr(tool, "id", None) is not None
        }
        tool_messages: list[dict[str, str]] = []
        for tool_call in tool_calls:
            tool = available_tools.get(tool_call.name)
            requested_tool_summary = {
                "name": tool_call.name,
                "arguments": dict(tool_call.arguments),
            }
            self._append_message(
                discussion_id,
                "Assistant",
                "Tool call requested:\n"
                f"{json.dumps(requested_tool_summary, ensure_ascii=True, sort_keys=True)}",
            )
            if tool is None:
                self._set_activity(
                    discussion_id,
                    stage="tool",
                    tool={**requested_tool_summary, "status": "denied"},
                )
                tool_messages.append(
                    {
                        "role": "user",
                        "content": format_tool_result_message(
                            tool_name=tool_call.name,
                            status="denied",
                            error="Tool is unavailable for this agent.",
                        ),
                    }
                )
                self._append_message(
                    discussion_id,
                    "Assistant",
                    format_tool_result_message(
                        tool_name=tool_call.name,
                        status="denied",
                        error="Tool is unavailable for this agent.",
                    ),
                )
                continue

            self._set_activity(
                discussion_id,
                stage="tool",
                tool={
                    "name": tool_call.name,
                    "arguments": dict(tool_call.arguments),
                    "status": "running",
                    "tool_id": getattr(tool, "id", None),
                },
            )
            result = tool_manager.execute_tool_call(
                ToolCall(
                    tool_id=int(tool.id),
                    arguments=tool_call.arguments,
                    requester_agent_id=agent_id,
                    discussion_id=discussion_id,
                )
            )
            tool_messages.append(
                {
                    "role": "user",
                    "content": format_tool_result_message(
                        tool_name=tool_call.name,
                        status=result.status,
                        result=result.result,
                        error=result.error,
                    ),
                }
            )
            self._append_message(
                discussion_id,
                "Assistant",
                format_tool_result_message(
                    tool_name=tool_call.name,
                    status=result.status,
                    result=result.result,
                    error=result.error,
                ),
            )
            self._set_activity(
                discussion_id,
                stage="generating",
                tool={
                    "name": tool_call.name,
                    "arguments": dict(tool_call.arguments),
                    "status": result.status,
                    "tool_id": getattr(tool, "id", None),
                    "error": result.error,
                    "metadata": dict(getattr(result, "metadata", {}) or {}),
                },
            )
        return tool_messages

    def _set_agentic_idle_activity(
        self,
        discussion_id: str,
        *,
        agent_name: str | None = None,
        speaker_name: str | None = None,
    ) -> None:
        self._set_activity(
            discussion_id,
            stage="idle",
            agent_name=agent_name,
            speaker_name=speaker_name,
            agent_mode="agentic",
            nudge=(
                "Agentic mode is active. The agent is idle now, so it is okay to pause or send "
                "another prompt if you want it to keep going."
            ),
        )

    def _get_discussion(self, discussion_id: str) -> Discussion | None:
        row = self._ensure_store.get("discussions", discussion_id=discussion_id)
        discussion = self._discussion_from_row(row)
        if discussion is not None and discussion.deleted_at is None:
            return discussion
        return None

    def _update_discussion(self, discussion_id: str, data: dict) -> None:
        row = self._ensure_store.get("discussions", discussion_id=discussion_id)
        if not row:
            raise ValueError(f"Discussion not found: {discussion_id}")
        current = self._discussion_from_row(row)
        if current is None:
            raise ValueError(f"Discussion not found: {discussion_id}")
        payload = self._discussion_to_store_payload(current)
        payload.update(data)
        payload["updated_at"] = utc_now_iso()
        self._ensure_store.update("discussions", where={"id": row["id"]}, data=payload)

    def _create_discussion(
        self,
        owner_user_id: int,
        title: str = "Untitled Discussion",
        group_id: int | None = None,
        folder_id: int | None = None,
        focused_wiki_id: str | None = None,
        participant_agent_ids: list[int] | None = None,
        chat_mode: str = "round_robin",
        chat_pause_seconds: float | None = None,
        chat_is_paused: bool = False,
        chat_turn_index: int = 0,
        chat_coordinator_agent_id: int | None = None,
        system_prompt: str = "",
    ) -> dict:
        discussion_id = _new_discussion_id()
        now = utc_now()
        discussion = Discussion(
            id=discussion_id,
            owner_user_id=owner_user_id,
            title=title,
            group_id=group_id,
            visibility="group" if group_id is not None else "private",
            folder_id=folder_id,
            focused_wiki_id=focused_wiki_id,
            participant_agent_ids=list(participant_agent_ids or []),
            chat_mode=chat_mode,
            chat_pause_seconds=chat_pause_seconds,
            chat_is_paused=chat_is_paused,
            chat_turn_index=chat_turn_index,
            chat_coordinator_agent_id=chat_coordinator_agent_id,
            system_prompt=system_prompt,
            created_at=now,
            updated_at=now,
        )
        self._ensure_store.insert("discussions", self._discussion_to_store_payload(discussion))
        return self._discussion_to_public_dict(discussion)

    def _set_current_discussion(self, user_id: int, discussion_id: str) -> None:
        row = self._ensure_store.get("discussion_user_state", user_id=user_id)
        if row:
            self._ensure_store.update(
                "discussion_user_state",
                where={"id": row["id"]},
                data={"user_id": user_id, "current_discussion_id": discussion_id},
            )
        else:
            self._ensure_store.insert(
                "discussion_user_state",
                {"user_id": user_id, "current_discussion_id": discussion_id},
            )

    def _get_current_discussion_id(self, user_id: int) -> str | None:
        row = self._ensure_store.get("discussion_user_state", user_id=user_id)
        if not row:
            return None
        current_discussion_id = row.get("current_discussion_id")
        return None if current_discussion_id is None else str(current_discussion_id)

    def _clear_current_discussion(self, user_id: int) -> None:
        row = self._ensure_store.get("discussion_user_state", user_id=user_id)
        if row:
            self._ensure_store.update(
                "discussion_user_state",
                where={"id": row["id"]},
                data={"user_id": user_id, "current_discussion_id": None},
            )

    def _is_visible(self, discussion: Discussion, user_id: int, member_group_ids: set[int]) -> bool:
        if discussion.deleted_at is not None:
            return False
        owner_user_id = discussion.owner_user_id or 0
        if owner_user_id == user_id:
            return True

        group_id = discussion.group_id
        if group_id is None:
            return False
        return group_id in member_group_ids

    def _list_visible_discussions(self, user_id: int, member_group_ids: set[int]) -> list[Discussion]:
        return [
            discussion
            for discussion in (
                self._discussion_from_row(row) for row in self._ensure_store.find("discussions")
            )
            if discussion is not None and self._is_visible(discussion, user_id, member_group_ids)
        ]

    def _get_current_visible_discussion(self, user_id: int, member_group_ids: set[int]) -> Discussion | None:
        current_discussion_id = self._get_current_discussion_id(user_id)
        if not current_discussion_id:
            return None
        current = self._get_discussion(current_discussion_id)
        if current and self._is_visible(current, user_id, member_group_ids):
            return current
        return None

    def _record_agent_participation(self, discussion_id: str, agent_id: int | None) -> None:
        if agent_id is None:
            return
        discussion = self._get_discussion(discussion_id)
        if discussion is None:
            raise ValueError(f"Discussion not found: {discussion_id}")
        if agent_id in discussion.participant_agent_ids:
            return
        self._update_discussion(
            discussion_id,
            {"participant_agent_ids": [*discussion.participant_agent_ids, int(agent_id)]},
        )

    def _resolve_group_chat_participants(
        self,
        discussion: Discussion,
        *,
        anchor_agent_id: int | None = None,
    ) -> list[GroupChatParticipant]:
        participants: list[GroupChatParticipant] = []
        seen: set[int] = set()

        if anchor_agent_id is not None:
            anchor = self._get_agent(anchor_agent_id)
            if anchor is not None and anchor.id is not None:
                participant_id = int(anchor.id)
                participants.append(
                    GroupChatParticipant(
                        agent_id=participant_id,
                        name=str(anchor.name or f"Agent {participant_id}"),
                    )
                )
                seen.add(participant_id)

        source_agent_ids = list(discussion.participant_agent_ids)
        if not source_agent_ids and discussion.group_id is not None:
            try:
                memberships = get_group_manager().list_group_members(int(discussion.group_id))
            except Exception:
                memberships = []
            for membership in memberships:
                agent_id = safe_int(getattr(membership, "agent_id", None), default=None)
                if agent_id is None:
                    continue
                member_kind = getattr(membership, "member_kind", None)
                member_kind_value = getattr(member_kind, "value", member_kind)
                if str(member_kind_value).strip().lower() != "agent":
                    continue
                if not bool(getattr(membership, "is_enabled", True)):
                    continue
                source_agent_ids.append(agent_id)

        for raw_agent_id in source_agent_ids:
            agent_id = safe_int(raw_agent_id, default=None)
            if agent_id is None or agent_id in seen:
                continue
            agent = self._get_agent(agent_id)
            if agent is None:
                continue
            participants.append(
                GroupChatParticipant(
                    agent_id=agent_id,
                    name=str(agent.name or f"Agent {agent_id}"),
                )
            )
            seen.add(agent_id)

        return participants

    def _append_group_chat_turn(
        self,
        discussion_id: str,
        *,
        speaker_name: str,
        text: str,
    ) -> None:
        self._append_group_agent_message(discussion_id, speaker_name=speaker_name, text=text)

    def _build_group_chat_prompt(
        self,
        *,
        discussion: Discussion,
        mode: str,
        speaker_name: str,
        original_prompt: str,
        coordinator_agent_id: int | None = None,
    ) -> str:
        from apmatia.lib.discussions.group_chat import build_turn_prompt

        _ = original_prompt
        return build_turn_prompt(
            mode=mode if mode in {"direct", "auto_paced", "continuous"} else "round_robin",
            speaker_name=speaker_name,
            coordinator_agent_id=coordinator_agent_id,
        )

    def _build_group_chat_system_prompt(
        self,
        *,
        discussion: Discussion,
        participant_names: list[str],
        turn_name: str,
        turn_mode: str,
        agent_prompt: str,
    ) -> str:
        instructions: list[str] = []
        discussion_prompt = discussion.system_prompt.strip()
        if discussion_prompt:
            instructions.append(discussion_prompt)

        roster = ", ".join(participant_names)
        if roster:
            instructions.append(f"Participants in this discussion: {roster}.")
        instructions.append(
            "Identity rules: you are only the current speaker for this turn and you must not "
            "claim to be any other participant. Preserve each participant's name and role exactly "
            "as written in the transcript."
        )
        instructions.append(f"Current speaker for this turn: {turn_name}.")
        instructions.append(
            f"Operating mode: {turn_mode}. Speak naturally as {turn_name} and avoid saying you have nothing to add unless the transcript truly leaves no relevant response. If you would otherwise say that, give one concrete observation, question, or next step instead."
        )
        if agent_prompt.strip():
            instructions.append(agent_prompt.strip())
        return "\n\n".join(instructions).strip()

    def _run_group_chat_turns(
        self,
        *,
        discussion_id: str,
        prompt: str,
        discussion: Discussion,
        agent_id: int | None,
        stop_event: threading.Event | None,
        current_attachments: list[dict[str, Any]] | None = None,
    ) -> None:
        existing_content = self._discussion_path(discussion_id).read_text(encoding="utf-8") if self._discussion_path(discussion_id).exists() else ""
        base_system_prompt = discussion.system_prompt
        wiki_context = ""
        if discussion.focused_wiki_id:
            wiki = get_wiki_manager().get_wiki(str(discussion.focused_wiki_id))
            wiki_title = None if wiki is None else wiki.title
            wiki_context = (
                "Current tutor session wiki:\n"
                f"- wiki_id: {discussion.focused_wiki_id}\n"
                f"- wiki_title: {wiki_title or 'Unknown wiki'}\n"
                "This wiki is already attached to the discussion. "
                "Do not ask the user for a wiki ID when using wiki tools."
            )

        participants = self._resolve_group_chat_participants(discussion, anchor_agent_id=agent_id)
        participant_names = [participant.name for participant in participants]
        plan = build_group_chat_plan(
            mode=discussion.chat_mode,
            participants=participants,
            current_turn_index=discussion.chat_turn_index,
            anchor_agent_id=agent_id,
            pause_seconds=discussion.chat_pause_seconds,
            coordinator_agent_id=discussion.chat_coordinator_agent_id,
        )
        if discussion.chat_mode == "direct":
            plan = build_group_chat_plan(
                mode=discussion.chat_mode,
                participants=participants,
                current_turn_index=discussion.chat_turn_index,
                anchor_agent_id=agent_id,
                direct_recipient_ids=discussion.participant_agent_ids,
                pause_seconds=discussion.chat_pause_seconds,
                coordinator_agent_id=discussion.chat_coordinator_agent_id,
            )

        if not plan.turns:
            raise RuntimeError("No group chat participants are available.")

        if prompt.strip():
            self._append_message(
                discussion_id,
                "User",
                prompt,
                metadata={"attachments": current_attachments} if current_attachments else None,
            )
            existing_content = self._discussion_path(discussion_id).read_text(encoding="utf-8")

        interrupted = False
        for turn in plan.turns:
            if stop_event is not None and stop_event.is_set():
                interrupted = True
                break

            agent = self._get_agent(turn.speaker_agent_id)
            if agent is None or agent.id is None:
                continue

            agent_prompt = self._resolve_agent_system_prompt(int(agent.id))
            llm_config = self._resolve_agent_llm_config(int(agent.id))
            system_prompt = self._build_group_chat_system_prompt(
                discussion=discussion,
                participant_names=participant_names,
                turn_name=turn.speaker_name,
                turn_mode=plan.mode,
                agent_prompt=agent_prompt,
            )
            available_tools = self._list_tools_available_to_agent(int(agent.id))
            if wiki_context:
                system_prompt = f"{system_prompt}\n\n{wiki_context}".strip()
            system_prompt = extend_system_prompt_with_tools(system_prompt, available_tools)
            chat_messages = build_chat_messages(
                existing_content=existing_content,
                system_prompt=system_prompt,
                current_prompt=self._build_group_chat_prompt(
                    discussion=discussion,
                    mode=plan.mode,
                    speaker_name=turn.speaker_name,
                    original_prompt=prompt,
                    coordinator_agent_id=plan.coordinator_agent_id,
                ),
                current_attachments=current_attachments,
                attachment_resolver=lambda attachment, discussion_id=discussion_id: self._attachment_content_parts(discussion_id, attachment),
            )
            assistant_writer = self._new_assistant_stream_writer(
                discussion_id,
                role="Agent",
                speaker_name=turn.speaker_name,
            )
            self._set_activity(
                discussion_id,
                **self._prompt_activity_summary(
                    discussion_id=discussion_id,
                    agent=agent,
                    speaker_name=turn.speaker_name,
                    llm_config=llm_config,
                    chat_messages=chat_messages,
                    prompt=prompt,
                ),
            )
            streamed_reply, final_reply, turn_stats = self._stream_assistant_iteration(
                discussion_id=discussion_id,
                prompt=prompt,
                chat_messages=chat_messages,
                llm_config=llm_config,
                stop_event=stop_event,
                assistant_writer=assistant_writer,
                agent_id=int(agent.id),
                speaker_name=turn.speaker_name,
            )
            clean_reply = strip_tool_calls(final_reply).strip() or strip_tool_calls(streamed_reply).strip()
            if assistant_writer.visible_char_count == 0:
                clean_reply = clean_reply or "I do not have a substantive reply yet, but I am following the discussion."
                assistant_writer.append(clean_reply)
            assistant_writer.append_metadata(turn_stats)
            existing_content = self._discussion_path(discussion_id).read_text(encoding="utf-8")

            if plan.continue_automatically and plan.pause_seconds:
                if stop_event is not None and stop_event.wait(plan.pause_seconds):
                    interrupted = True
                    break

        self._update_discussion(
            discussion_id,
            {
                "chat_turn_index": plan.next_turn_index,
                "chat_is_paused": interrupted,
                "last_error": None,
            },
        )

    def _get_or_create_current_discussion(self, user_id: int, member_group_ids: set[int]) -> Discussion:
        current = self._get_current_visible_discussion(user_id, member_group_ids)
        if current is not None:
            return current

        created = self._create_discussion(owner_user_id=user_id, title="New Discussion")
        self._set_current_discussion(user_id, created["discussion_id"])
        current = self._get_discussion(str(created["discussion_id"]))
        if current is None:
            raise RuntimeError("Failed to create current discussion.")
        return current

    def _trash_payload(self) -> dict:
        now = datetime.now(timezone.utc)
        purge_after = now + timedelta(days=TRASH_RETENTION_DAYS)
        return {
            "deleted_at": now.isoformat(),
            "purge_after": purge_after.isoformat(),
        }

    def _collect_descendant_folder_ids(self, owner_user_id: int, root_folder_id: int) -> list[int]:
        folders = self._ensure_store.find("discussion_folders", owner_user_id=owner_user_id)
        by_parent: dict[str, list[dict]] = {}
        for folder in folders:
            parent_key = "root" if folder.get("parent_id") is None else str(folder.get("parent_id"))
            by_parent.setdefault(parent_key, []).append(folder)

        collected: list[int] = []
        stack: list[int] = [int(root_folder_id)]
        seen: set[int] = set()
        while stack:
            current = int(stack.pop())
            if current in seen:
                continue
            seen.add(current)
            collected.append(current)
            for child in by_parent.get(str(current), []):
                child_id = int(child.get("id", 0))
                if child_id > 0:
                    stack.append(child_id)
        return collected

    def _purge_expired_trash(self, owner_user_id: int) -> None:
        now = datetime.now(timezone.utc)
        folders = self._ensure_store.find("discussion_folders", owner_user_id=owner_user_id)
        for folder in folders:
            deleted_at = parse_iso_datetime(folder.get("deleted_at"))
            if deleted_at is None:
                continue
            purge_after = parse_iso_datetime(folder.get("purge_after")) or (
                deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
            )
            if purge_after <= now:
                self._store.delete("discussion_folders", id=int(folder["id"]))

        discussions = self._store.find("discussions", owner_user_id=owner_user_id)
        for discussion_row in discussions:
            discussion = self._discussion_from_row(discussion_row)
            if discussion is None:
                continue
            deleted_at = parse_iso_datetime(discussion.deleted_at)
            if deleted_at is None:
                continue
            purge_after = parse_iso_datetime(discussion.purge_after) or (
                deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
            )
            if purge_after <= now:
                self._ensure_store.delete("discussions", id=int(discussion_row["id"]))
                discussion_id = discussion.discussion_id
                if discussion_id:
                    try:
                        self._discussion_path(discussion_id).unlink(missing_ok=True)
                    except OSError:
                        pass

    def _run_prompt(self, discussion_id: str, prompt: str, agent_id: int | None = None) -> None:
        preserve_activity = False
        try:
            stop_event = self._stop_events.get(discussion_id)
            discussion = self._get_discussion(discussion_id)
            if not discussion:
                raise RuntimeError(f"Discussion not found: {discussion_id}")
            current_attachments = self._get_pending_prompt_attachments(discussion_id)

            if normalize_group_chat_mode(discussion.chat_mode) != "single":
                self._run_group_chat_turns(
                    discussion_id=discussion_id,
                    prompt=prompt,
                    discussion=discussion,
                    agent_id=agent_id,
                    stop_event=stop_event,
                    current_attachments=current_attachments,
                )
                return

            discussion_path = self._discussion_path(discussion_id)
            existing_content = discussion_path.read_text(encoding="utf-8") if discussion_path.exists() else ""
            system_prompt = discussion.system_prompt
            speaker_name = None
            agent: Agent | None = None
            if agent_id is not None:
                agent = self._get_agent(agent_id)
                speaker_name = None if agent is None else str(agent.name or f"Agent {agent_id}")
            wiki_context = ""
            if discussion.focused_wiki_id:
                wiki = get_wiki_manager().get_wiki(str(discussion.focused_wiki_id))
                wiki_title = None if wiki is None else wiki.title
                wiki_context = (
                    "Current tutor session wiki:\n"
                    f"- wiki_id: {discussion.focused_wiki_id}\n"
                    f"- wiki_title: {wiki_title or 'Unknown wiki'}\n"
                    "This wiki is already attached to the discussion. "
                    "Do not ask the user for a wiki ID when using wiki tools."
                )
            available_tools: list[Any] = []
            if agent_id is not None:
                system_prompt = self._resolve_agent_system_prompt(agent_id)
                available_tools = self._list_tools_available_to_agent(agent_id)
            if wiki_context:
                system_prompt = f"{system_prompt}\n\n{wiki_context}".strip()
            system_prompt = extend_system_prompt_with_tools(system_prompt, available_tools)
            chat_messages = build_chat_messages(
                existing_content=existing_content,
                system_prompt=system_prompt,
                current_prompt=prompt,
                current_attachments=current_attachments,
                attachment_resolver=lambda attachment, discussion_id=discussion_id: self._attachment_content_parts(discussion_id, attachment),
            )
            self._append_message(
                discussion_id,
                "User",
                prompt,
                metadata={"attachments": current_attachments} if current_attachments else None,
            )
            llm_config = self._resolve_agent_llm_config(agent_id) if agent_id is not None else None
            if agent is not None and speaker_name is not None:
                self._set_activity(
                    discussion_id,
                    **self._prompt_activity_summary(
                        discussion_id=discussion_id,
                        agent=agent,
                        speaker_name=speaker_name,
                        llm_config=llm_config,
                        chat_messages=chat_messages,
                        prompt=prompt,
                    ),
                )
            assistant_writer = self._new_assistant_stream_writer(discussion_id)
            final_reply = ""

            if agent_id is not None:
                last_turn_stats: dict[str, Any] | None = None
                for _ in range(3):
                    streamed_reply, final_reply, turn_stats = self._stream_assistant_iteration(
                        discussion_id=discussion_id,
                        prompt=prompt,
                        chat_messages=chat_messages,
                        llm_config=llm_config,
                        stop_event=stop_event,
                        assistant_writer=assistant_writer,
                        agent_id=agent_id,
                        speaker_name=speaker_name,
                    )
                    last_turn_stats = turn_stats
                    final_reply = final_reply.strip()
                    requested_tool_calls = parse_tool_calls(final_reply)
                    if not requested_tool_calls:
                        break
                    chat_messages.append(
                        {
                            "role": "assistant",
                            "content": final_reply or streamed_reply or "I will use the requested tools.",
                        }
                    )
                    chat_messages.extend(
                        self._execute_tool_calls(
                            agent_id=agent_id,
                            discussion_id=discussion_id,
                            tool_calls=requested_tool_calls,
                        )
                    )
                else:
                    pass
            else:
                _, final_reply, last_turn_stats = self._stream_assistant_iteration(
                    discussion_id=discussion_id,
                    prompt=prompt,
                    chat_messages=chat_messages,
                    llm_config=llm_config,
                    stop_event=stop_event,
                    assistant_writer=assistant_writer,
                )

            clean_reply = strip_tool_calls(final_reply).strip()
            if assistant_writer.visible_char_count == 0:
                fallback_reply = clean_reply or "I could not produce a final reply after tool execution."
                assistant_writer.append(fallback_reply)
            assistant_writer.append_metadata(last_turn_stats)
            self._update_discussion(discussion_id, {"last_error": None})
            preserve_activity = False
            current_discussion = self._get_discussion(discussion_id)
            if (
                agent_id is not None
                and current_discussion is not None
                and current_discussion.agent_mode == "agentic"
                and (stop_event is None or not stop_event.is_set())
            ):
                self._set_agentic_idle_activity(
                    discussion_id,
                    agent_name=None if agent is None else str(agent.name or f"Agent {agent_id}"),
                    speaker_name=speaker_name,
                )
                preserve_activity = True
        except Exception as error:
            self._update_discussion(discussion_id, {"last_error": str(error)})
        finally:
            if not preserve_activity:
                self._clear_activity(discussion_id)
            with self._lock:
                self._streaming.discard(discussion_id)
                self._threads.pop(discussion_id, None)
                self._stop_events.pop(discussion_id, None)

    def _stream_assistant_iteration(
        self,
        *,
        discussion_id: str,
        prompt: str,
        chat_messages: list[dict[str, str]],
        llm_config: LLM | None,
        stop_event: threading.Event | None,
        assistant_writer: "_AssistantTranscriptWriter",
        agent_id: int | None = None,
        speaker_name: str | None = None,
    ) -> tuple[str, str, dict[str, Any] | None]:
        stream_filter = ToolCallStreamFilter()
        stream_state = {"chunk_count": 0, "visible_characters": 0}
        final_stats: dict[str, Any] | None = None

        def on_chunk(chunk: str) -> None:
            nonlocal final_stats
            visible_chunk = stream_filter.push(chunk)
            if visible_chunk:
                stream_state["chunk_count"] += 1
                stream_state["visible_characters"] += len(visible_chunk)
            assistant_writer.append(visible_chunk)
            if agent_id is not None:
                self._set_activity(
                    discussion_id,
                    stage="generating",
                    agent_id=agent_id,
                    speaker_name=speaker_name,
                    stream=dict(stream_state),
                )

        def on_event(event: dict[str, Any]) -> None:
            nonlocal final_stats
            if not isinstance(event, dict):
                return
            stats = event.get("stats")
            if not isinstance(stats, dict):
                stats = {}
            usage = event.get("usage")
            if isinstance(usage, dict):
                stats = {**stats, "usage": usage}
            if "raw" in event and isinstance(event["raw"], dict):
                raw_event = event["raw"]
                for key in ("usage", "prompt_eval_count", "eval_count", "prompt_tokens", "completion_tokens", "total_tokens"):
                    if key in raw_event:
                        stats[key] = raw_event[key]
            if not stats:
                return
            final_stats = dict(stats)
            self._set_activity(
                discussion_id,
                stage="generating",
                agent_id=agent_id,
                speaker_name=speaker_name,
                stats=stats,
                stream=dict(stream_state),
            )

        raw_reply = self._call_llm(
            discussion_id=discussion_id,
            prompt=prompt,
            chat_messages=chat_messages,
            llm_config=llm_config,
            stop_event=stop_event,
            on_chunk=on_chunk,
            on_event=on_event,
        )
        assistant_writer.append(stream_filter.finalize())
        llama_status = self._llama_server_status()
        if self._llama_server_status_has_renderable_metrics(llama_status):
            final_stats = llama_status
        elif not self._llama_server_status_has_renderable_metrics(final_stats):
            final_stats = None
        return strip_tool_calls(raw_reply).strip(), raw_reply, final_stats

    def create_folder(self, owner_user_id: int, name: str, parent_id: int | None = None) -> dict:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Folder name cannot be empty.")

        if parent_id is not None:
            parent = self._ensure_store.get("discussion_folders", id=parent_id)
            if not parent or int(parent.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Parent folder not found.")

        created_at = utc_now_iso()
        folder = {
            "name": clean_name,
            "parent_id": parent_id,
            "owner_user_id": owner_user_id,
            "deleted_at": None,
            "purge_after": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
        folder_id = self._ensure_store.insert("discussion_folders", folder)
        return {"id": folder_id, **folder}

    def update_folder(
        self,
        owner_user_id: int,
        folder_id: int,
        name: str | None | object = _UNSET,
        parent_id: int | None | object = _UNSET,
    ) -> dict:
        folder = self._ensure_store.get("discussion_folders", id=folder_id)
        if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
            raise ValueError("Folder not found.")
        if folder.get("deleted_at") is not None:
            raise ValueError("Folder not found.")

        updates: dict = {}
        if name is not _UNSET and name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Folder name cannot be empty.")
            updates["name"] = clean_name

        if parent_id is not _UNSET:
            if parent_id is None:
                updates["parent_id"] = None
            else:
                next_parent_id = int(parent_id)
                if next_parent_id == folder_id:
                    raise ValueError("Folder cannot be its own parent.")
                descendant_ids = set(self._collect_descendant_folder_ids(owner_user_id, folder_id))
                if next_parent_id in descendant_ids:
                    raise ValueError("Folder cannot be moved into itself or its descendants.")
                parent = self._ensure_store.get("discussion_folders", id=next_parent_id)
                if not parent or int(parent.get("owner_user_id", -1)) != owner_user_id:
                    raise ValueError("Parent folder not found.")
                if parent.get("deleted_at") is not None:
                    raise ValueError("Parent folder not found.")
                updates["parent_id"] = next_parent_id

        if updates:
            updates["updated_at"] = utc_now_iso()
            self._ensure_store.update("discussion_folders", where={"id": folder_id}, data=updates)

        merged = {**folder, **updates}
        return merged

    def delete_folder(self, owner_user_id: int, folder_id: int, force: bool = False) -> dict:
        folder = self._ensure_store.get("discussion_folders", id=folder_id)
        if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
            raise ValueError("Folder not found.")
        if folder.get("deleted_at") is not None:
            raise ValueError("Folder is already in trash.")

        subtree_folder_ids = self._collect_descendant_folder_ids(owner_user_id, folder_id)
        folder_ids_set = set(subtree_folder_ids)

        all_owned_discussions = self._ensure_store.find("discussions", owner_user_id=owner_user_id)
        contained_discussions = [
            discussion
            for discussion in (self._discussion_from_row(row) for row in all_owned_discussions)
            if discussion is not None and discussion.deleted_at is None and (discussion.folder_id in folder_ids_set)
        ]
        has_contents = bool(len(subtree_folder_ids) > 1 or contained_discussions)
        if has_contents and not force:
            raise ValueError("Folder is not empty.")

        trash = self._trash_payload()
        touched_at = utc_now_iso()

        for subfolder_id in subtree_folder_ids:
            self._ensure_store.update(
                "discussion_folders",
                where={"id": int(subfolder_id)},
                data={**trash, "updated_at": touched_at},
            )

        for discussion in contained_discussions:
            self._update_discussion(discussion.discussion_id, {**trash, "updated_at": touched_at})

        return {
            "id": int(folder_id),
            "trashed_folders": len(subtree_folder_ids),
            "trashed_discussions": len(contained_discussions),
        }

    def restore_folder(self, owner_user_id: int, folder_id: int) -> dict:
        folder = self._store.get("discussion_folders", id=folder_id)
        if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
            raise ValueError("Folder not found.")
        if folder.get("deleted_at") is None:
            raise ValueError("Folder is not in trash.")

        subtree_folder_ids = self._collect_descendant_folder_ids(owner_user_id, folder_id)
        folder_ids_set = set(subtree_folder_ids)

        all_owned_discussions = self._store.find("discussions", owner_user_id=owner_user_id)
        contained_discussions = [
            discussion
            for discussion in (self._discussion_from_row(row) for row in all_owned_discussions)
            if discussion is not None and discussion.deleted_at is not None and (discussion.folder_id in folder_ids_set)
        ]

        touched_at = utc_now_iso()
        for subfolder_id in subtree_folder_ids:
            self._store.update(
                "discussion_folders",
                where={"id": int(subfolder_id)},
                data={"deleted_at": None, "purge_after": None, "updated_at": touched_at},
            )

        for discussion in contained_discussions:
            self._update_discussion(
                discussion.discussion_id,
                {"deleted_at": None, "purge_after": None, "updated_at": touched_at},
            )

        return {
            "id": int(folder_id),
            "restored_folders": len(subtree_folder_ids),
            "restored_discussions": len(contained_discussions),
        }

    def restore_discussion(self, owner_user_id: int, discussion_id: str) -> dict:
        discussion_row = self._store.get("discussions", discussion_id=discussion_id)
        discussion = self._discussion_from_row(discussion_row)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")
        if discussion.deleted_at is None:
            raise ValueError("Discussion is not in trash.")

        restored_folder_id = discussion.folder_id
        if restored_folder_id is not None:
            folder = self._ensure_store.get("discussion_folders", id=restored_folder_id)
            if (
                not folder
                or int(folder.get("owner_user_id", -1)) != owner_user_id
                or folder.get("deleted_at") is not None
            ):
                restored_folder_id = None

        self._ensure_store.update(
            "discussions",
            where={"id": int(discussion_row["id"])},
            data={
                "folder_id": restored_folder_id,
                "deleted_at": None,
                "purge_after": None,
                "updated_at": utc_now_iso(),
            },
        )
        return {"discussion_id": str(discussion_id), "folder_id": restored_folder_id}

    def delete_discussion(self, owner_user_id: int, discussion_id: str) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")

        self._update_discussion(discussion_id, {**self._trash_payload(), "updated_at": utc_now_iso()})
        next_discussion_id: str | None = None
        current_discussion_id = self._get_current_discussion_id(owner_user_id)
        if current_discussion_id == str(discussion_id):
            remaining = [
                candidate
                for candidate in self._list_visible_discussions(owner_user_id, set())
                if candidate.discussion_id != str(discussion_id)
            ]
            remaining.sort(key=lambda item: item.updated_at, reverse=True)
            next_discussion_id = remaining[0].discussion_id if remaining else None
            if next_discussion_id is None:
                self._clear_current_discussion(owner_user_id)
            else:
                self._set_current_discussion(owner_user_id, next_discussion_id)
        return {"discussion_id": str(discussion_id), "next_discussion_id": next_discussion_id}

    def list_trash(self, owner_user_id: int) -> dict:
        self._purge_expired_trash(owner_user_id)
        folders = [
            folder
            for folder in self._ensure_store.find("discussion_folders", owner_user_id=owner_user_id)
            if folder.get("deleted_at") is not None
        ]
        discussions = [
            self._discussion_to_public_dict(discussion)
            for discussion in (
                self._discussion_from_row(row)
                for row in self._ensure_store.find("discussions", owner_user_id=owner_user_id)
            )
            if discussion is not None and discussion.deleted_at is not None
        ]
        return {"folders": folders, "discussions": discussions}

    def create_discussion(
        self,
        owner_user_id: int,
        title: str,
        group_id: int | None = None,
        folder_id: int | None = None,
        focused_wiki_id: str | None = None,
        agent_id: int | None = None,
        participant_agent_ids: list[int] | None = None,
        chat_mode: str = "round_robin",
        chat_pause_seconds: float | None = None,
        chat_coordinator_agent_id: int | None = None,
    ) -> dict:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Discussion title cannot be empty.")

        if folder_id is not None:
            folder = self._ensure_store.get("discussion_folders", id=folder_id)
            if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Folder not found.")
            if folder.get("deleted_at") is not None:
                raise ValueError("Folder not found.")

        created = self._create_discussion(
            owner_user_id=owner_user_id,
            title=clean_title,
            group_id=group_id,
            folder_id=folder_id,
            focused_wiki_id=focused_wiki_id,
            participant_agent_ids=[
                *([] if participant_agent_ids is None else [int(candidate) for candidate in participant_agent_ids]),
                *([] if agent_id is None else [int(agent_id)]),
            ],
            chat_mode=chat_mode,
            chat_pause_seconds=chat_pause_seconds,
            chat_coordinator_agent_id=chat_coordinator_agent_id,
        )
        return created

    def update_discussion(
        self,
        owner_user_id: int,
        discussion_id: str,
        title: str | None | object = _UNSET,
        group_id: int | None | object = _UNSET,
        folder_id: int | None | object = _UNSET,
        focused_wiki_id: str | None | object = _UNSET,
        participant_agent_ids: list[int] | None | object = _UNSET,
        agent_mode: str | None | object = _UNSET,
        chat_mode: str | None | object = _UNSET,
        chat_pause_seconds: float | None | object = _UNSET,
        chat_is_paused: bool | object = _UNSET,
        chat_turn_index: int | None | object = _UNSET,
        chat_coordinator_agent_id: int | None | object = _UNSET,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")

        updates: dict = {}
        if title is not _UNSET and title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Discussion title cannot be empty.")
            updates["title"] = clean_title

        if group_id is not _UNSET:
            updates["group_id"] = group_id
            updates["visibility"] = "group" if group_id is not None else "private"

        if folder_id is not _UNSET:
            if folder_id is None:
                updates["folder_id"] = None
            else:
                next_folder_id = int(folder_id)
                folder = self._ensure_store.get("discussion_folders", id=next_folder_id)
                if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
                    raise ValueError("Folder not found.")
                if folder.get("deleted_at") is not None:
                    raise ValueError("Folder not found.")
                updates["folder_id"] = next_folder_id

        if focused_wiki_id is not _UNSET:
            updates["focused_wiki_id"] = None if focused_wiki_id is None else str(focused_wiki_id).strip() or None

        if participant_agent_ids is not _UNSET:
            updates["participant_agent_ids"] = [
                agent_id
                for agent_id in (
                    safe_int(candidate, default=None) for candidate in (participant_agent_ids or [])
                )
                if agent_id is not None
            ]
        if agent_mode is not _UNSET:
            updates["agent_mode"] = _normalize_agent_mode(agent_mode)

        if chat_mode is not _UNSET:
            updates["chat_mode"] = normalize_group_chat_mode(chat_mode)
        if chat_pause_seconds is not _UNSET:
            updates["chat_pause_seconds"] = None if chat_pause_seconds is None else float(chat_pause_seconds)
        if chat_is_paused is not _UNSET:
            updates["chat_is_paused"] = bool(chat_is_paused)
        if chat_turn_index is not _UNSET:
            updates["chat_turn_index"] = max(0, safe_int(chat_turn_index, default=0) or 0)
        if chat_coordinator_agent_id is not _UNSET:
            updates["chat_coordinator_agent_id"] = safe_int(chat_coordinator_agent_id, default=None)

        self._update_discussion(discussion_id, updates)
        refreshed = self._get_discussion(discussion_id)
        if refreshed is None:
            raise ValueError("Discussion not found.")
        return self._discussion_to_public_dict(refreshed)

    def set_chat_mode(
        self,
        *,
        user_id: int,
        discussion_id: str,
        member_group_ids: set[int],
        chat_mode: str,
        chat_pause_seconds: float | None = None,
        chat_coordinator_agent_id: int | None = None,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or not self._is_visible(discussion, user_id, member_group_ids):
            raise ValueError("Discussion not found.")
        self._update_discussion(
            discussion_id,
            {
                "chat_mode": normalize_group_chat_mode(chat_mode),
                "chat_pause_seconds": chat_pause_seconds,
                "chat_coordinator_agent_id": chat_coordinator_agent_id,
                "chat_is_paused": False,
                "chat_turn_index": 0,
            },
        )
        refreshed = self._get_discussion(discussion_id)
        if refreshed is None:
            raise ValueError("Discussion not found.")
        return self._discussion_to_public_dict(refreshed)

    def set_agent_mode(
        self,
        *,
        discussion_id: str,
        mode: str,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if discussion is None:
            raise ValueError("Discussion not found.")

        normalized_mode = _normalize_agent_mode(mode)
        previous_mode = discussion.agent_mode
        self._update_discussion(
            discussion_id,
            {"agent_mode": normalized_mode},
        )
        refreshed = self._get_discussion(discussion_id)
        if refreshed is None:
            raise ValueError("Discussion not found.")
        status = "unchanged" if previous_mode == refreshed.agent_mode else "updated"
        payload = self._discussion_to_public_dict(refreshed)
        payload.update(
            {
                "previous_mode": previous_mode,
                "current_mode": refreshed.agent_mode,
                "status": status,
            }
        )
        return payload

    def pause_group_chat(self, user_id: int, member_group_ids: set[int]) -> str:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        if normalize_group_chat_mode(current.chat_mode) == "single":
            raise RuntimeError("The current discussion is not running in group chat mode.")
        self._update_discussion(
            current.discussion_id,
            {"chat_is_paused": True, "last_error": None},
        )
        with self._lock:
            stop_event = self._stop_events.get(current.discussion_id)
            if stop_event is not None:
                stop_event.set()
            self._streaming.discard(current.discussion_id)
        return current.discussion_id

    def resume_group_chat(self, user_id: int, member_group_ids: set[int]) -> str:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        if normalize_group_chat_mode(current.chat_mode) == "single":
            raise RuntimeError("The current discussion is not running in group chat mode.")
        if not current.chat_is_paused:
            raise RuntimeError("The current discussion is not paused.")

        with self._lock:
            if current.discussion_id in self._streaming:
                raise RuntimeError("A discussion response is already streaming.")

            stop_event = threading.Event()
            self._stop_events[current.discussion_id] = stop_event
            self._streaming.add(current.discussion_id)
            self._update_discussion(current.discussion_id, {"last_error": None, "chat_is_paused": False})
            thread = threading.Thread(
                target=self._run_prompt,
                args=(current.discussion_id, "", None),
                daemon=True,
            )
            self._threads[current.discussion_id] = thread
            thread.start()
        return current.discussion_id

    def open_discussion(self, user_id: int, discussion_id: str, member_group_ids: set[int]) -> None:
        discussion = self._get_discussion(discussion_id)
        if not discussion or not self._is_visible(discussion, user_id, member_group_ids):
            raise ValueError("Discussion not found.")
        self._set_current_discussion(user_id, discussion_id)

    def list_tree(self, user_id: int, member_group_ids: set[int]) -> dict:
        self._purge_expired_trash(user_id)
        folders = [
            folder
            for folder in self._ensure_store.find("discussion_folders", owner_user_id=user_id)
            if folder.get("deleted_at") is None
        ]
        all_discussions = self._list_visible_discussions(user_id, member_group_ids)
        visible = [
            self._discussion_to_public_dict(discussion)
            for discussion in all_discussions
        ]
        current = self._get_current_visible_discussion(user_id, member_group_ids)
        current_discussion_id = None if current is None else current.discussion_id
        return {
            "current_discussion_id": current_discussion_id,
            "folders": folders,
            "discussions": visible,
        }

    def start_prompt(
        self,
        user_id: int,
        prompt: str,
        member_group_ids: set[int],
        agent_id: int | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str:
        with self._lock:
            discussion = self._get_or_create_current_discussion(user_id, member_group_ids)
            discussion_id = discussion.discussion_id
            if discussion_id in self._streaming:
                raise RuntimeError("A discussion response is already streaming.")
            self._record_agent_participation(discussion_id, agent_id)
            stored_attachments = self._store_prompt_attachments(discussion_id, attachments)
            if stored_attachments:
                self._pending_prompt_attachments[discussion_id] = stored_attachments

            stop_event = threading.Event()
            self._stop_events[discussion_id] = stop_event
            self._streaming.add(discussion_id)
            self._update_discussion(discussion_id, {"last_error": None})
            thread = threading.Thread(
                target=self._run_prompt,
                args=(discussion_id, prompt, agent_id),
                daemon=True,
            )
            self._threads[discussion_id] = thread
            thread.start()
            return discussion_id

    def reset_discussion(self, user_id: int) -> str:
        with self._lock:
            current = self._get_or_create_current_discussion(user_id, set())
            current_id = current.discussion_id
            if current_id in self._streaming:
                raise RuntimeError("Cannot reset while a response is still streaming.")

            created = self._create_discussion(
                owner_user_id=user_id,
                title="New Discussion",
                system_prompt=current.system_prompt,
            )
            self._set_current_discussion(user_id, created["discussion_id"])
            return str(created["discussion_id"])

    def set_system_prompt(self, user_id: int, system_prompt: str, member_group_ids: set[int]) -> None:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        self._update_discussion(
            current.discussion_id,
            {"system_prompt": system_prompt},
        )

    def snapshot(self, user_id: int, member_group_ids: set[int]) -> DiscussionSnapshot:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        discussion_id = current.discussion_id
        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        messages = self._parse_messages(content)
        messages = [self._hydrate_message_attachments(discussion_id, message) for message in messages]
        turns = self._llama_server_turns()
        assistant_messages = [message for message in messages if str(message.get("role", "")).strip().lower() != "user"]
        if turns and assistant_messages:
            for message, turn in zip(assistant_messages, turns[-len(assistant_messages) :]):
                metadata = message.get("metadata")
                llama_status = metadata.get("llama_server_status") if isinstance(metadata, dict) else None
                if isinstance(llama_status, dict) and not self._llama_server_status_has_renderable_metrics(llama_status):
                    message["metadata"] = {"llama_server_status": turn}

        with self._lock:
            is_streaming = discussion_id in self._streaming
            activity = self._activity.get(discussion_id)

        return DiscussionSnapshot(
            discussion_id=discussion_id,
            is_streaming=is_streaming,
            last_error=current.last_error,
            agent_mode=current.agent_mode,
            chat_mode=current.chat_mode,
            chat_pause_seconds=current.chat_pause_seconds,
            chat_is_paused=current.chat_is_paused,
            chat_turn_index=current.chat_turn_index,
            chat_coordinator_agent_id=current.chat_coordinator_agent_id,
            system_prompt=current.system_prompt,
            content=content,
            messages=messages,
            activity=None if activity is None else dict(activity),
            llama_server_status=self._llama_server_status(),
        )

    def update_message(
        self,
        *,
        owner_user_id: int,
        discussion_id: str,
        message_index: int,
        text: str,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")
        if message_index < 0:
            raise ValueError("Message not found.")

        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        messages = self._parse_messages(content)
        if message_index >= len(messages):
            raise ValueError("Message not found.")

        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Message cannot be empty.")

        messages[message_index]["text"] = cleaned_text
        path.write_text(self._format_messages(messages), encoding="utf-8")
        self._update_discussion(discussion_id, {"last_error": None})
        return {"discussion_id": discussion_id, "message_index": message_index}

    def delete_message(
        self,
        *,
        owner_user_id: int,
        discussion_id: str,
        message_index: int,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")
        if message_index < 0:
            raise ValueError("Message not found.")

        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        messages = self._parse_messages(content)
        if message_index >= len(messages):
            raise ValueError("Message not found.")

        del messages[message_index]
        path.write_text(self._format_messages(messages), encoding="utf-8")
        self._update_discussion(discussion_id, {"last_error": None, "chat_turn_index": 0})
        return {"discussion_id": discussion_id, "message_index": message_index}

    def delete_messages(
        self,
        *,
        owner_user_id: int,
        discussion_id: str,
        message_indices: list[int],
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or discussion.owner_user_id != owner_user_id:
            raise ValueError("Discussion not found.")

        cleaned_indices = sorted({int(index) for index in message_indices})
        if not cleaned_indices:
            raise ValueError("Select at least one message to delete.")
        if cleaned_indices[0] < 0:
            raise ValueError("Message not found.")

        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        messages = self._parse_messages(content)

        if cleaned_indices[-1] >= len(messages):
            raise ValueError("Message not found.")

        for message_index in sorted(cleaned_indices, reverse=True):
            del messages[message_index]

        path.write_text(self._format_messages(messages), encoding="utf-8")
        self._update_discussion(discussion_id, {"last_error": None, "chat_turn_index": 0})
        return {"discussion_id": discussion_id, "message_indices": cleaned_indices}

    def stop_prompt(self, user_id: int, member_group_ids: set[int]) -> str:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        discussion_id = current.discussion_id

        with self._lock:
            stop_event = self._stop_events.get(discussion_id)
            if stop_event is None or discussion_id not in self._streaming:
                raise RuntimeError("No discussion response is currently streaming.")
            stop_event.set()

        return discussion_id


discussion_state = DiscussionState()
