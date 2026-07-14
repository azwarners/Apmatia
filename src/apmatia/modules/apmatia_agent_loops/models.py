from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from apmatia.lib.apmatia_core.models import ApmatiaObject, utc_now


class TaskStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_REACHED = "limit_reached"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_REACHED = "limit_reached"


class LoopEventType(str, Enum):
    TASK_STARTED = "task_started"
    MODEL_TURN_STARTED = "model_turn_started"
    MODEL_TURN_COMPLETED = "model_turn_completed"
    MODEL_ACTIVITY = "model_activity"
    TOOL_REQUESTED = "tool_requested"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    CANCELLATION_REQUESTED = "cancellation_requested"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    EXECUTION_LIMIT_REACHED = "execution_limit_reached"


def new_task_id() -> str:
    return f"loop_{uuid4().hex}"


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {item.name: _serialize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


@dataclass(slots=True)
class CancellationToken:
    cancelled: bool = False

    def is_cancelled(self) -> bool:
        return self.cancelled

    def cancel(self) -> None:
        self.cancelled = True


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ToolRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: f"call_{uuid4().hex}")

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ToolRequest":
        return cls(
            tool_name=str(payload.get("tool_name") or payload.get("name") or "").strip(),
            arguments=dict(payload.get("arguments") or {}),
            call_id=str(payload.get("call_id") or payload.get("id") or f"call_{uuid4().hex}"),
        )


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    call_id: str
    status: str
    output: Any = None
    error: str | None = None
    raw_result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ToolResult":
        return cls(
            tool_name=str(payload.get("tool_name") or "").strip(),
            call_id=str(payload.get("call_id") or "").strip(),
            status=str(payload.get("status") or "failed").strip(),
            output=payload.get("output"),
            error=None if payload.get("error") in (None, "") else str(payload.get("error")),
            raw_result=payload.get("raw_result"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class ToolContext:
    task_id: str
    task: "AgentLoopTask"
    turn_index: int
    tool_call_index: int
    available_tools: tuple[ToolDefinition, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ModelUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ModelRequest:
    task_id: str
    task: "AgentLoopTask"
    turn_index: int
    available_tools: tuple[ToolDefinition, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    prior_events: tuple["LoopEvent", ...] = ()
    activity_sink: Any = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ModelResponse:
    final_text: str | None = None
    tool_requests: tuple[ToolRequest, ...] = ()
    usage: ModelUsage | None = None
    raw_response: Any = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class LoopEvent:
    event_type: LoopEventType
    task_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoopEvent":
        created_at_raw = payload.get("created_at")
        created_at = utc_now()
        if isinstance(created_at_raw, str) and created_at_raw.strip():
            try:
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except ValueError:
                created_at = utc_now()
        return cls(
            event_type=LoopEventType(str(payload.get("event_type") or payload.get("type") or "").strip()),
            task_id=str(payload.get("task_id") or "").strip(),
            payload=dict(payload.get("payload") or payload.get("data") or {}),
            created_at=created_at,
        )


@dataclass(slots=True)
class AgentLoopTask(ApmatiaObject):
    title: str = ""
    contact_kind: str = ""
    contact_id: str | int | None = None
    prompt: str = ""
    checklist: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    participant_agent_ids: tuple[int, ...] = field(default_factory=tuple)
    agent_id: int | None = None
    selected_model_id: int | None = None
    chat_mode: str = "single"
    allow_tools: bool = True
    max_model_turns: int = 5
    max_tool_calls: int = 10
    timeout_seconds: float | None = None
    status: TaskStatus = TaskStatus.DRAFT
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    stop_requested: bool = False
    current_turn: int = 0
    tool_call_count: int = 0
    final_text: str | None = None
    summary: str | None = None
    last_error: str | None = None
    workspace_root: str = ""
    knowledge_root: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    events: tuple[LoopEvent, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentLoopTask":
        events = tuple(
            LoopEvent.from_dict(item)
            for item in list(payload.get("events") or [])
            if isinstance(item, dict)
        )
        checklist = tuple(
            dict(item)
            for item in list(payload.get("checklist") or [])
            if isinstance(item, dict)
        )
        participant_agent_ids = tuple(
            int(item)
            for item in list(payload.get("participant_agent_ids") or [])
            if str(item).strip()
        )
        return cls(
            id=payload.get("id"),
            owner_user_id=payload.get("owner_user_id"),
            owner_group_id=payload.get("owner_group_id"),
            mode=int(payload.get("mode") or 0),
            created_at=datetime.fromisoformat(str(payload.get("created_at")).replace("Z", "+00:00"))
            if payload.get("created_at")
            else utc_now(),
            updated_at=datetime.fromisoformat(str(payload.get("updated_at")).replace("Z", "+00:00"))
            if payload.get("updated_at")
            else utc_now(),
            title=str(payload.get("title") or ""),
            contact_kind=str(payload.get("contact_kind") or ""),
            contact_id=payload.get("contact_id"),
            prompt=str(payload.get("prompt") or ""),
            checklist=checklist,
            participant_agent_ids=participant_agent_ids,
            agent_id=None if payload.get("agent_id") in (None, "") else int(payload.get("agent_id")),
            selected_model_id=None if payload.get("selected_model_id") in (None, "") else int(payload.get("selected_model_id")),
            chat_mode=str(payload.get("chat_mode") or "single"),
            allow_tools=bool(payload.get("allow_tools", True)),
            max_model_turns=int(payload.get("max_model_turns") or 5),
            max_tool_calls=int(payload.get("max_tool_calls") or 10),
            timeout_seconds=payload.get("timeout_seconds"),
            status=TaskStatus(str(payload.get("status") or TaskStatus.DRAFT.value)),
            execution_status=ExecutionStatus(str(payload.get("execution_status") or ExecutionStatus.PENDING.value)),
            stop_requested=bool(payload.get("stop_requested", False)),
            current_turn=int(payload.get("current_turn") or 0),
            tool_call_count=int(payload.get("tool_call_count") or 0),
            final_text=None if payload.get("final_text") in (None, "") else str(payload.get("final_text")),
            summary=None if payload.get("summary") in (None, "") else str(payload.get("summary")),
            last_error=None if payload.get("last_error") in (None, "") else str(payload.get("last_error")),
            workspace_root=str(payload.get("workspace_root") or ""),
            knowledge_root=str(payload.get("knowledge_root") or ""),
            metadata=dict(payload.get("metadata") or {}),
            events=events,
        )


@dataclass(slots=True)
class AgentLoopExecutionRequest:
    task_id: str


@dataclass(slots=True)
class AgentLoopExecutionResult:
    task_id: str
    status: ExecutionStatus
    final_text: str | None
    task: AgentLoopTask
    events: tuple[LoopEvent, ...]
    model_turns: int
    tool_calls: int
    stop_reason: str | None = None
    raw_response: Any = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


def update_task_status(task: AgentLoopTask, *, status: TaskStatus, execution_status: ExecutionStatus, **updates: Any) -> AgentLoopTask:
    return replace(
        task,
        status=status,
        execution_status=execution_status,
        updated_at=utc_now(),
        **updates,
    )
