from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from apmatia.core.models import ApmatiaObject


def new_tool_call_id() -> str:
    return f"call_{uuid4().hex}"


@dataclass(slots=True)
class ToolDefinition(ApmatiaObject):
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    provider_id: str = ""
    enabled: bool = True
    confirmation_required: bool = False
    read_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentToolAssignment:
    id: int | None = None
    agent_id: int = 0
    tool_id: int = 0
    enabled: bool = True
    confirmation_required: bool | None = None
    read_only: bool | None = None


@dataclass(slots=True)
class ToolCall:
    tool_id: int
    arguments: dict[str, Any] = field(default_factory=dict)
    requester_agent_id: int = 0
    discussion_id: str | None = None
    call_id: str = field(default_factory=new_tool_call_id)


@dataclass(slots=True)
class ToolResult:
    call_id: str
    status: str
    result: Any = None
    error: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
