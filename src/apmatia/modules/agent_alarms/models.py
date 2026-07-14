from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from apmatia.lib.apmatia_core.models import ApmatiaObject, utc_now


class AlarmStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not value:
        return utc_now()
    raw = str(value).strip()
    if not raw:
        return utc_now()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return utc_now()
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


@dataclass(slots=True)
class AgentAlarm(ApmatiaObject):
    name: str = ""
    agent_id: int = 0
    prompt: str = ""
    model_id: int = 0
    scheduled_start_time: datetime = field(default_factory=utc_now)
    enabled: bool = True
    status: AlarmStatus = AlarmStatus.SCHEDULED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    launched_loop_run_id: str | None = None
    last_result: str | None = None
    last_error: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.name = str(self.name or "").strip()
        self.prompt = str(self.prompt or "").strip()
        self.agent_id = int(self.agent_id)
        self.model_id = int(self.model_id)
        self.scheduled_start_time = _parse_datetime(self.scheduled_start_time)
        self.enabled = bool(self.enabled)
        self.status = self._normalize_status(self.status)
        self.started_at = None if self.started_at in (None, "") else _parse_datetime(self.started_at)
        self.completed_at = None if self.completed_at in (None, "") else _parse_datetime(self.completed_at)
        self.launched_loop_run_id = None if self.launched_loop_run_id in (None, "") else str(self.launched_loop_run_id).strip()
        self.last_result = None if self.last_result in (None, "") else str(self.last_result).strip()
        self.last_error = None if self.last_error in (None, "") else str(self.last_error).strip()

    @staticmethod
    def _normalize_status(value: Any) -> AlarmStatus:
        if isinstance(value, AlarmStatus):
            return value
        candidate = str(value or AlarmStatus.SCHEDULED.value).strip().lower()
        try:
            return AlarmStatus(candidate)
        except ValueError:
            return AlarmStatus.SCHEDULED

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentAlarm":
        return cls(
            id=payload.get("id"),
            owner_user_id=payload.get("owner_user_id"),
            owner_group_id=payload.get("owner_group_id"),
            mode=payload.get("mode", 0),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            name=payload.get("name", ""),
            agent_id=payload.get("agent_id", 0),
            prompt=payload.get("prompt", ""),
            model_id=payload.get("model_id", 0),
            scheduled_start_time=payload.get("scheduled_start_time"),
            enabled=payload.get("enabled", True),
            status=payload.get("status", AlarmStatus.SCHEDULED.value),
            started_at=payload.get("started_at"),
            completed_at=payload.get("completed_at"),
            launched_loop_run_id=payload.get("launched_loop_run_id"),
            last_result=payload.get("last_result"),
            last_error=payload.get("last_error"),
        )
