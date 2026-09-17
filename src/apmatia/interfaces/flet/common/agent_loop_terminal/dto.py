"""Small typed DTOs used at the shared Agent Loop terminal boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentLoopEventDto:
    sequence: int
    event_type: str
    payload: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentLoopEventDto":
        return cls(
            sequence=int(value["sequence"]),
            event_type=str(value.get("event_type") or ""),
            payload=dict(value.get("payload") or {}),
        )


@dataclass(frozen=True, slots=True)
class AgentLoopTaskDto:
    task_id: str
    status: str
    events: tuple[AgentLoopEventDto, ...] = ()
    pending_tool_call: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentLoopTaskDto":
        events = tuple(
            AgentLoopEventDto.from_dict(event)
            for event in value.get("events") or ()
            if isinstance(event, dict) and event.get("sequence") not in (None, "")
        )
        return cls(
            task_id=str(value.get("id") or ""),
            status=str(value.get("status") or "idle"),
            events=events,
            pending_tool_call=value.get("pending_tool_call"),
        )
