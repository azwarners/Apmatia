from __future__ import annotations

import os
import tempfile
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from apmatia.lib.apmatia_core.models import utc_now

from .models import (
    Discussion,
    DiscussionParticipant,
    DiscussionTurn,
    SUMMARY_REASONS,
    TOPIC_STATUSES,
    Topic,
    TopicSummary,
    TopicTransitionDecision,
)
from .sqlite_repositories import TopicManagementBundle


_EXPLICIT_TOPIC_CHANGE_PHRASES = (
    "new topic",
    "change topics",
    "switch topics",
    "split topic",
    "move discussion",
    "move this discussion",
    "different subject",
)

DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path(tempfile.gettempdir()) / "apmatia"))
).expanduser()
CONTACTS_AND_DISCUSSIONS_DB = DATA_DIR / "contacts_and_discussions.db"


class TopicTransitionDetector:
    def assess(
        self,
        *,
        prompt: str,
        current_topic: Topic | None = None,
        last_activity_at: datetime | None = None,
        keywords: Sequence[str] | None = None,
        explicit_action: str | None = None,
        moved_discussion: bool = False,
    ) -> TopicTransitionDecision:
        action = str(explicit_action or "").strip().lower()
        if action in {"new_topic", "split_topic", "move_topic"}:
            return TopicTransitionDecision(
                decision=action,
                source="explicit",
                confidence=1.0,
                reason="An explicit user action selected the next topic state.",
                suggested_topic_title=_derive_topic_title(prompt, current_topic=current_topic),
            )

        prompt_text = str(prompt or "").strip()
        prompt_lower = prompt_text.lower()
        if prompt_lower:
            for phrase in _EXPLICIT_TOPIC_CHANGE_PHRASES:
                if phrase in prompt_lower:
                    return TopicTransitionDecision(
                        decision="new_topic",
                        source="heuristic",
                        confidence=0.96,
                        reason=f"Prompt contained an explicit topic shift phrase: {phrase!r}.",
                        suggested_topic_title=_derive_topic_title(prompt_text, current_topic=current_topic),
                    )

        if moved_discussion:
            return TopicTransitionDecision(
                decision="move_topic",
                source="heuristic",
                confidence=0.92,
                reason="The discussion was moved elsewhere.",
                suggested_topic_title=_derive_topic_title(prompt_text, current_topic=current_topic),
            )

        if last_activity_at is not None:
            idle_minutes = max(0.0, (utc_now() - last_activity_at).total_seconds() / 60.0)
            if idle_minutes >= 120:
                return TopicTransitionDecision(
                    decision="new_topic",
                    source="heuristic",
                    confidence=0.9,
                    reason=f"The discussion has been idle for about {idle_minutes:.0f} minutes.",
                    suggested_topic_title=_derive_topic_title(prompt_text, current_topic=current_topic),
                )
            if idle_minutes >= 45 and _looks_like_new_subject(prompt_text, keywords=keywords, current_topic=current_topic):
                return TopicTransitionDecision(
                    decision="new_topic",
                    source="heuristic",
                    confidence=0.74,
                    reason="Idle time plus a low-overlap prompt suggests a new topic.",
                    suggested_topic_title=_derive_topic_title(prompt_text, current_topic=current_topic),
                )

        if _looks_like_new_subject(prompt_text, keywords=keywords, current_topic=current_topic):
            return TopicTransitionDecision(
                decision="confirm_with_llm",
                source="llm_confirmation",
                confidence=0.4,
                reason="Heuristics detected a possible topic shift but not enough to decide confidently.",
                suggested_topic_title=_derive_topic_title(prompt_text, current_topic=current_topic),
            )

        return TopicTransitionDecision(
            decision="stay",
            source="heuristic",
            confidence=0.8,
            reason="No strong evidence for a topic transition was detected.",
            suggested_topic_title=None if current_topic is None else current_topic.title or None,
        )


class TopicManagementService:
    def __init__(self, bundle: TopicManagementBundle | None = None):
        self.bundle = bundle or TopicManagementBundle(CONTACTS_AND_DISCUSSIONS_DB)
        self.transition_detector = TopicTransitionDetector()

    def list_topics(self) -> list[Topic]:
        return self.bundle.topics.list_all()

    def list_discussions(self, *, topic_id: str | int | None = None) -> list[Discussion]:
        if topic_id is None:
            return self.bundle.discussions.list_all()
        return self.bundle.discussions.list_by_topic(topic_id)

    def list_participants(self, *, discussion_id: str | int | None = None) -> list[DiscussionParticipant]:
        if discussion_id is None:
            return self.bundle.participants.list_all()
        return self.bundle.participants.list_by_discussion(discussion_id)

    def list_summaries(self, *, topic_id: str | int | None = None) -> list[TopicSummary]:
        if topic_id is None:
            return self.bundle.summaries.list_all()
        return self.bundle.summaries.list_by_topic(topic_id)

    def list_turns(self, *, discussion_id: str | int | None = None) -> list[DiscussionTurn]:
        turns = self.bundle.turns.list_all() if discussion_id is None else self.bundle.turns.list_by_discussion(discussion_id)
        return sorted(turns, key=lambda item: (int(item.turn_index), item.created_at))

    def create_topic(self, topic: Topic) -> Topic:
        created = replace(topic, id=self.bundle.topics.create(topic))
        return created

    def create_discussion(self, discussion: Discussion) -> Discussion:
        if discussion.topic_id is None:
            raise ValueError("A discussion must belong to a topic.")
        created = replace(discussion, id=self.bundle.discussions.create(discussion))
        return created

    def create_participant(self, participant: DiscussionParticipant) -> DiscussionParticipant:
        if participant.discussion_id is None and participant.agent_id is None and participant.group_id is None:
            raise ValueError("A participant must select an agent or group.")
        created = replace(participant, id=self.bundle.participants.create(participant))
        return created

    def record_turn(self, turn: DiscussionTurn) -> DiscussionTurn:
        if turn.discussion_id is None or turn.topic_id is None:
            raise ValueError("A turn must belong to a topic and discussion.")
        created = replace(turn, id=self.bundle.turns.create(turn))
        self._touch_discussion(turn.discussion_id)
        return created

    def create_summary(self, summary: TopicSummary) -> TopicSummary:
        if summary.topic_id is None:
            raise ValueError("A summary must belong to a topic.")
        created = replace(summary, id=self.bundle.summaries.create(summary))
        self._attach_summary_to_topic(summary.topic_id, created.id)
        if summary.discussion_id is not None:
            self._attach_summary_to_discussion(summary.discussion_id, created.id)
        return created

    def detect_topic_transition(
        self,
        *,
        prompt: str,
        topic_id: str | int | None = None,
        explicit_action: str | None = None,
        moved_discussion: bool = False,
    ) -> TopicTransitionDecision:
        topic = None if topic_id is None else self.bundle.topics.get(topic_id)
        last_activity_at = None
        if topic is not None:
            discussions = self.bundle.discussions.list_by_topic(topic.id)
            last_activity_at = max(
                (discussion.last_activity_at for discussion in discussions if discussion.last_activity_at is not None),
                default=None,
            )
        keywords = _extract_keywords(topic)
        return self.transition_detector.assess(
            prompt=prompt,
            current_topic=topic,
            last_activity_at=last_activity_at,
            keywords=keywords,
            explicit_action=explicit_action,
            moved_discussion=moved_discussion,
        )

    def draft_topic_summary(
        self,
        *,
        topic_id: str | int,
        reason: str = "maintenance",
        discussion_id: str | int | None = None,
        created_by_agent_id: int | None = None,
        max_turns: int = 8,
    ) -> TopicSummary:
        if reason not in SUMMARY_REASONS:
            raise ValueError(f"Unsupported summary reason: {reason}")
        topic = self.bundle.topics.get(topic_id)
        if topic is None:
            raise ValueError("Topic not found.")

        turns = self.bundle.turns.list_all() if discussion_id is None else self.bundle.turns.list_by_discussion(discussion_id)
        selected_turns = sorted(turns, key=lambda item: (item.turn_index, item.created_at))[-max_turns:]
        lines = [
            f"Topic: {topic.title}",
            f"Reason: {reason.replace('_', ' ')}",
        ]
        if topic.description:
            lines.append(f"Context: {topic.description}")
        if selected_turns:
            lines.append("Recent work:")
            for turn in selected_turns:
                snippet = turn.content.strip().replace("\n", " ")
                if len(snippet) > 160:
                    snippet = f"{snippet[:157]}..."
                lines.append(f"- {snippet}")
        else:
            lines.append("Recent work: no recorded turns yet.")

        title = _summary_title(topic.title, reason)
        summary = TopicSummary(
            topic_id=topic.id,
            discussion_id=discussion_id,
            reason=reason,
            title=title,
            body="\n".join(lines),
            created_by_agent_id=created_by_agent_id,
            source_turn_ids=[turn.id for turn in selected_turns if turn.id is not None],
            created_at=utc_now(),
        )
        return self.create_summary(summary)

    def close_topic(self, topic_id: str | int) -> Topic:
        topic = self.bundle.topics.get(topic_id)
        if topic is None:
            raise ValueError("Topic not found.")
        updated = replace(topic, status="closed", updated_at=utc_now())
        self.bundle.topics.update(updated)
        return updated

    def _touch_discussion(self, discussion_id: str | int) -> None:
        discussion = self.bundle.discussions.get(discussion_id)
        if discussion is None:
            return
        now = utc_now()
        updated = replace(discussion, last_activity_at=now, updated_at=now)
        self.bundle.discussions.update(updated)

    def _attach_summary_to_topic(self, topic_id: str | int, summary_id: str | int | None) -> None:
        topic = self.bundle.topics.get(topic_id)
        if topic is None:
            return
        updated = replace(topic, summary_id=summary_id, updated_at=utc_now())
        self.bundle.topics.update(updated)

    def _attach_summary_to_discussion(self, discussion_id: str | int, summary_id: str | int | None) -> None:
        discussion = self.bundle.discussions.get(discussion_id)
        if discussion is None:
            return
        updated = replace(discussion, summary_id=summary_id, updated_at=utc_now())
        self.bundle.discussions.update(updated)


def _extract_keywords(topic: Topic | None) -> list[str]:
    if topic is None:
        return []
    keywords = [topic.title, topic.description, *topic.tags]
    normalized: list[str] = []
    for value in keywords:
        for token in str(value).replace("/", " ").replace("-", " ").split():
            token = token.strip().lower()
            if len(token) >= 4 and token not in normalized:
                normalized.append(token)
    return normalized


def _looks_like_new_subject(
    prompt: str,
    *,
    keywords: Sequence[str] | None,
    current_topic: Topic | None,
) -> bool:
    prompt_tokens = _tokenize(prompt)
    if not prompt_tokens:
        return False

    keyword_set = {keyword.lower() for keyword in (keywords or []) if keyword}
    overlap = len(keyword_set.intersection(prompt_tokens))
    if keyword_set and overlap > 0:
        return False
    if current_topic is not None and current_topic.title:
        title_tokens = _tokenize(current_topic.title)
        if title_tokens and len(title_tokens.intersection(prompt_tokens)) > 0:
            return False
    return len(prompt_tokens) >= 3


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in str(text or "").replace("/", " ").replace("-", " ").split():
        token = "".join(ch for ch in raw.lower() if ch.isalnum())
        if len(token) >= 4:
            tokens.add(token)
    return tokens


def _derive_topic_title(prompt: str, *, current_topic: Topic | None) -> str | None:
    candidate = str(prompt or "").strip().splitlines()[0] if str(prompt or "").strip() else ""
    candidate = candidate[:80].strip(" :-")
    if not candidate:
        return None if current_topic is None else current_topic.title or None
    return candidate.title()


def _summary_title(topic_title: str, reason: str) -> str:
    base = str(topic_title or "Topic").strip() or "Topic"
    suffix = reason.replace("_", " ").strip().title()
    return f"{base} Summary - {suffix}"


# ---------------------------------------------------------------------------
# prompt_llm – thin wrapper around ysparr for use by other modules
# ---------------------------------------------------------------------------
import sys
import uuid
import json
from threading import Event
from pathlib import Path
from typing import Callable

from apmatia.core.app_config import get_config_value
from apmatia.modules.ai_model_manager.models import LLMConfig as _LLMConfig

try:
    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        OpenAICompatibleBackend,
    )
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage
except ModuleNotFoundError:
    _ysparr_path = Path(__file__).resolve().parents[4] / "src" / "apmatia" / "lib" / "ysparr"
    if str(_ysparr_path) not in sys.path:
        sys.path.insert(0, str(_ysparr_path))
    from ysparr.core.types import PromptRequest  # noqa: E402
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend  # noqa: E402
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (  # noqa: E402
        OpenAICompatibleBackend,
    )
    from ysparr.modalities.text2text.executor import execute  # noqa: E402
    from ysparr.modalities.text2text.storage import TextFileStorage  # noqa: E402


class _ChunkCallbackStorage(TextFileStorage):
    def __init__(self, output_dir: str, *, on_chunk: Callable[[str], None] | None = None) -> None:
        super().__init__(output_dir)
        self._on_chunk = on_chunk

    def append(self, request: "PromptRequest", text: str) -> None:
        super().append(request, text)
        if self._on_chunk is not None and text:
            self._on_chunk(text)


def _resolve_model_name(llm_config: _LLMConfig | None) -> str:
    if llm_config is not None:
        provider_name = str(getattr(llm_config, "provider_name", "") or "").strip()
        if not provider_name:
            provider_name = str(getattr(llm_config, "provider_model_name", "") or "").strip()
        if provider_name:
            return provider_name
        model_name = str(getattr(llm_config, "user_alias", "") or "").strip()
        if not model_name:
            model_name = str(getattr(llm_config, "model_name", "") or "").strip()
        if model_name:
            return model_name
    model_name = (
        get_config_value("llm", "model_name", default=None)
        or os.getenv("LLM_MODEL")
        or "default"
    )
    return str(model_name)


def _build_backend(llm_config: _LLMConfig | None = None):
    backend_name = (
        (llm_config.backend if llm_config is not None else None)
        or get_config_value("llm", "backend", default=None)
        or os.getenv("YSPARR_TEXT2TEXT_BACKEND")
        or "openai_compatible"
    ).strip().lower()
    
    # Debug: Log backend configuration
    if os.getenv("APMATIA_DEBUG_BACKEND", "0") == "1":
        print(f"[_build_backend] backend_name={backend_name}")
        print(f"[_build_backend] llm_config.model_url={llm_config.model_url if llm_config else None}")
        print(f"[_build_backend] llm_config.api_key={llm_config.api_key if llm_config else None}")

    if backend_name in {"openai", "openai_compatible", "openai-compatible"}:
        base_url = (
            (llm_config.model_url if llm_config is not None else None)
            or get_config_value("llm", "openai_compatible", "base_url", default=None)
            or os.getenv("OPENAI_COMPAT_BASE_URL")
        )
        api_key = (
            (llm_config.api_key if llm_config is not None else None)
            or get_config_value("llm", "openai_compatible", "api_key", default=None)
            or os.getenv("OPENAI_COMPAT_API_KEY")
        )
        model_name = (
            _resolve_model_name(llm_config)
            or get_config_value("llm", "openai_compatible", "model_name", default=None)
            or os.getenv("OPENAI_COMPAT_MODEL")
        )
        
        if os.getenv("APMATIA_DEBUG_BACKEND", "0") == "1":
            print(f"[_build_backend] OpenAICompatibleBackend config:")
            print(f"[_build_backend]   base_url={base_url}")
            print(f"[_build_backend]   api_key={api_key[:10]}..." if api_key else f"[_build_backend]   api_key=None")
            print(f"[_build_backend]   model_name={model_name}")
        
        return OpenAICompatibleBackend(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            timeout_seconds=None,
        )

    return KoboldCppBackend(
        base_url=(
            (llm_config.model_url if llm_config is not None else None)
            or get_config_value("llm", "koboldcpp", "base_url", default=None)
            or os.getenv("KOBOLDCPP_URL")
            or "http://localhost:5001"
        )
    )


def _default_generation_parameters(llm_config: _LLMConfig | None = None) -> dict[str, Any]:
    max_tokens_value = (
        (llm_config.max_response_size if llm_config is not None else None)
        or get_config_value("llm", "max_tokens", default=None)
        or os.getenv("LLM_MAX_TOKENS")
        or 8192
    )
    max_tokens = int(max_tokens_value)
    return {"max_tokens": max_tokens}


def prompt_llm(
    prompt: str = "Hello",
    output_dir: str | None = None,
    prompt_id: str | None = None,
    append_existing: bool = False,
    context: str | None = None,
    request_metadata: dict[str, Any] | None = None,
    llm_config: _LLMConfig | None = None,
    stop_event: Event | None = None,
    on_chunk: Callable[[str], None] | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    conversation_mode = str((request_metadata or {}).get("conversation_mode") or "direct").strip().lower()
    speaker_name = str((request_metadata or {}).get("speaker_name") or "Assistant").strip()
    user_name = str((request_metadata or {}).get("user_name") or "User").strip()
    if conversation_mode == "group":
        current_turn = f"{user_name}: {prompt}\n{speaker_name}:"
        prompt_text = f"{context.rstrip()}\n{current_turn}" if context and context.strip() else current_turn
    elif context and context.strip():
        prompt_text = f"{context.rstrip()}\n{prompt}"
    else:
        prompt_text = prompt

    model_name = _resolve_model_name(llm_config)
    request = PromptRequest(
        prompt_id=prompt_id or str(uuid.uuid4()),
        prompt_text=prompt_text,
        model_name=model_name,
        parameters=_default_generation_parameters(llm_config),
        metadata={
            "append_existing": append_existing,
            **(request_metadata or {}),
            "on_event": on_event,
        },
        stop_event=stop_event,
    )

    backend = _build_backend(llm_config)
    apmatia_home = Path(
        os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))
    ).expanduser()
    resolved_output_dir = (
        Path(output_dir).expanduser()
        if output_dir is not None
        else apmatia_home / "prompt_logs"
    )
    if on_chunk is None:
        storage = TextFileStorage(str(resolved_output_dir))
    else:
        storage = _ChunkCallbackStorage(str(resolved_output_dir), on_chunk=on_chunk)
    result = execute(request, backend, storage)

    raw_text = Path(result.output_path).read_text(encoding="utf-8").strip()

    if append_existing:
        return raw_text

    try:
        payload = json.loads(raw_text)
        return payload["results"][0]["text"].strip()
    except Exception:
        return raw_text


# ---------------------------------------------------------------------------
# Discussion helpers used by other modules (get_discussion / set_agent_mode)
# ---------------------------------------------------------------------------
def get_discussion(discussion_id: str | int, *, bundle: TopicManagementBundle | None = None) -> Discussion | None:
    """Return a Discussion by id (or None if not found / deleted)."""
    bundle = bundle or TopicManagementBundle(CONTACTS_AND_DISCUSSIONS_DB)
    return bundle.discussions.get(discussion_id)


def set_agent_mode(
    discussion_id: str | int,
    mode: str,
    *,
    bundle: TopicManagementBundle | None = None,
) -> dict[str, Any]:
    """Set the agent_mode on a discussion. Returns a dict with status info."""
    bundle = bundle or TopicManagementBundle(CONTACTS_AND_DISCUSSIONS_DB)
    discussion = bundle.discussions.get(discussion_id)
    if discussion is None:
        raise ValueError(f"Discussion not found: {discussion_id}")

    normalized_mode = mode.strip().lower()
    if normalized_mode not in DISCUSSION_AGENT_MODES:
        raise ValueError(f"mode must be one of {DISCUSSION_AGENT_MODES}")

    previous_mode = discussion.agent_mode
    updated = replace(discussion, agent_mode=normalized_mode, updated_at=utc_now())
    bundle.discussions.update(updated)
    refreshed = bundle.discussions.get(discussion_id)
    if refreshed is None:
        raise ValueError(f"Discussion not found after update: {discussion_id}")

    status = "unchanged" if previous_mode == refreshed.agent_mode else "updated"
    return {
        "discussion_id": refreshed.id,
        "previous_mode": previous_mode,
        "current_mode": refreshed.agent_mode,
        "status": status,
    }
