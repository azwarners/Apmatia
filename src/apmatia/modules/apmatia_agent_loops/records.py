from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import contact_key, tasks_root


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_task_id() -> str:
    return f"loop-{uuid.uuid4().hex[:12]}"


def task_directory(contact_kind: str, contact_id: int | str) -> Path:
    return tasks_root() / contact_key(contact_kind, contact_id)


def task_record_path(contact_kind: str, contact_id: int | str, task_id: str) -> Path:
    return task_directory(contact_kind, contact_id) / f"{task_id}.json"


@dataclass(slots=True)
class LoopTaskRecord:
    task_id: str
    owner_user_id: int
    contact_kind: str
    contact_id: int | str
    title: str
    prompt: str
    checklist: list[dict[str, Any]] = field(default_factory=list)
    status: str = "queued"
    discussion_id: str | None = None
    agent_id: int | None = None
    participant_agent_ids: list[int] = field(default_factory=list)
    chat_mode: str = "single"
    allow_tools: bool = True
    max_iterations: int = 5
    current_iteration: int = 0
    stop_requested: bool = False
    loop_status: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    summary: str | None = None
    executive_analysis: str | None = None
    last_error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    completed_at: str | None = None
    workspace_root: str | None = None
    knowledge_root: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "owner_user_id": self.owner_user_id,
            "contact_kind": self.contact_kind,
            "contact_id": self.contact_id,
            "title": self.title,
            "prompt": self.prompt,
            "checklist": list(self.checklist),
            "status": self.status,
            "discussion_id": self.discussion_id,
            "agent_id": self.agent_id,
            "participant_agent_ids": list(self.participant_agent_ids),
            "chat_mode": self.chat_mode,
            "allow_tools": self.allow_tools,
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "stop_requested": self.stop_requested,
            "loop_status": self.loop_status,
            "events": list(self.events),
            "summary": self.summary,
            "executive_analysis": self.executive_analysis,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "workspace_root": self.workspace_root,
            "knowledge_root": self.knowledge_root,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoopTaskRecord":
        return cls(
            task_id=str(payload.get("task_id") or "").strip(),
            owner_user_id=int(payload.get("owner_user_id") or 0),
            contact_kind=str(payload.get("contact_kind") or "").strip(),
            contact_id=payload.get("contact_id"),
            title=str(payload.get("title") or ""),
            prompt=str(payload.get("prompt") or ""),
            checklist=[dict(item) for item in (payload.get("checklist") or []) if isinstance(item, dict)],
            status=str(payload.get("status") or "queued"),
            discussion_id=_optional_str(payload.get("discussion_id")),
            agent_id=_optional_int(payload.get("agent_id")),
            participant_agent_ids=[int(candidate) for candidate in (payload.get("participant_agent_ids") or []) if _is_int(candidate)],
            chat_mode=str(payload.get("chat_mode") or "single"),
            allow_tools=bool(payload.get("allow_tools", True)),
            max_iterations=max(1, _optional_int(payload.get("max_iterations"), default=5) or 5),
            current_iteration=max(0, _optional_int(payload.get("current_iteration"), default=0) or 0),
            stop_requested=bool(payload.get("stop_requested", False)),
            loop_status=payload.get("loop_status") if isinstance(payload.get("loop_status"), dict) else None,
            events=[dict(item) for item in (payload.get("events") or []) if isinstance(item, dict)],
            summary=_optional_str(payload.get("summary")),
            executive_analysis=_optional_str(payload.get("executive_analysis")),
            last_error=_optional_str(payload.get("last_error")),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            updated_at=str(payload.get("updated_at") or utc_now_iso()),
            completed_at=_optional_str(payload.get("completed_at")),
            workspace_root=_optional_str(payload.get("workspace_root")),
            knowledge_root=_optional_str(payload.get("knowledge_root")),
        )


def save_task_record(record: LoopTaskRecord) -> Path:
    path = task_record_path(record.contact_kind, record.contact_id, record.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.to_dict(), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def load_task_record(contact_kind: str, contact_id: int | str, task_id: str) -> LoopTaskRecord | None:
    path = task_record_path(contact_kind, contact_id, task_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return LoopTaskRecord.from_dict(payload)


def list_task_records(contact_kind: str | None = None, contact_id: int | str | None = None) -> list[LoopTaskRecord]:
    root = tasks_root()
    if not root.exists():
        return []

    records: list[LoopTaskRecord] = []
    contact_dirs: list[Path]
    if contact_kind is None or contact_id is None:
        contact_dirs = [candidate for candidate in root.iterdir() if candidate.is_dir()]
    else:
        contact_dirs = [task_directory(contact_kind, contact_id)]

    for contact_dir in contact_dirs:
        if not contact_dir.exists():
            continue
        for candidate in sorted(contact_dir.glob("*.json")):
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                record = LoopTaskRecord.from_dict(payload)
                if record.task_id:
                    records.append(record)

    records.sort(key=lambda record: record.updated_at, reverse=True)
    return records


def update_task_record(record: LoopTaskRecord, **updates: Any) -> LoopTaskRecord:
    payload = record.to_dict()
    payload.update(updates)
    payload["updated_at"] = utc_now_iso()
    updated = LoopTaskRecord.from_dict(payload)
    save_task_record(updated)
    return updated


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if not text else text


def _optional_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_int(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False
