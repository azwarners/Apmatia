"""Pure event reducer for the shared Agent Loop terminal."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentLoopTerminalState:
    agents: tuple[dict[str, Any], ...] = ()
    tasks: tuple[dict[str, Any], ...] = ()
    selected_agent_id: int | None = None
    selected_task_id: str | None = None
    events: dict[int, dict[str, Any]] = field(default_factory=dict)
    status: str = "idle"
    pending_approval: dict[str, Any] | None = None
    request_error: str | None = None

    @property
    def ordered_events(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.events[key] for key in sorted(self.events))

    @property
    def send_enabled(self) -> bool:
        return self.selected_task_id is not None and self.status in {"idle", "stopped"}


def request_failed(state: AgentLoopTerminalState, message: str) -> AgentLoopTerminalState:
    return replace(state, request_error=str(message))


def reduce_event(state: AgentLoopTerminalState, event: dict[str, Any]) -> AgentLoopTerminalState:
    sequence = event.get("sequence")
    if sequence in (None, ""):
        return state
    sequence = int(sequence)
    if sequence in state.events:
        return state
    events = dict(state.events)
    events[sequence] = dict(event)
    event_type = str(event.get("event_type") or "")
    pending = state.pending_approval
    status = state.status
    if event_type == "tool_awaiting_approval":
        pending = dict(event.get("payload") or {})
        status = "awaiting_approval"
    elif event_type in {"task_started", "model_turn_started", "tool_requested"}:
        status = "running"
    elif event_type == "task_stopped":
        status, pending = "stopped", None
    elif event_type == "task_archived":
        status, pending = "archived", None
    elif event_type in {"task_completed", "task_failed", "execution_limit_reached"}:
        status, pending = ("idle" if event_type == "task_completed" else "failed"), None
    return replace(state, events=events, status=status, pending_approval=pending, request_error=None)


def apply_task_snapshot(
    state: AgentLoopTerminalState, task: dict[str, Any]
) -> AgentLoopTerminalState:
    snapshot_status = str(task.get("status") or "idle")
    snapshot_pending = task.get("pending_tool_call")
    next_state = replace(
        state,
        selected_task_id=str(task.get("id") or state.selected_task_id or ""),
        status=snapshot_status,
        pending_approval=snapshot_pending,
        events={},
        request_error=None,
    )
    for event in task.get("events") or []:
        if isinstance(event, dict):
            next_state = reduce_event(next_state, event)
    # Historical approval events remain in the transcript after approval or
    # denial. Core's current snapshot is authoritative for live controls.
    live_pending = (
        dict(snapshot_pending)
        if snapshot_status == "awaiting_approval" and isinstance(snapshot_pending, dict)
        else None
    )
    if live_pending is not None:
        pending_call_id = str(live_pending.get("call_id") or "")
        pending_tool_name = str(live_pending.get("tool_name") or "")
        for event in reversed(next_state.ordered_events):
            if event.get("event_type") != "tool_awaiting_approval":
                continue
            payload = event.get("payload") or {}
            tool_call = payload.get("tool_call") or {}
            event_call_id = str(payload.get("call_id") or tool_call.get("call_id") or "")
            event_tool_name = str(payload.get("tool_name") or tool_call.get("tool_name") or "")
            if pending_call_id and event_call_id and pending_call_id != event_call_id:
                continue
            if pending_tool_name and event_tool_name and pending_tool_name != event_tool_name:
                continue
            for key in ("description", "read_only"):
                if key in payload:
                    live_pending[key] = payload[key]
            break
    return replace(next_state, status=snapshot_status, pending_approval=live_pending)
