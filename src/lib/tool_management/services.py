from __future__ import annotations

from typing import Any, Protocol

from .models import AgentToolAssignment, ToolCall, ToolDefinition, ToolResult


class ToolService(Protocol):
    def create_tool_definition(self, **kwargs: Any) -> ToolDefinition:
        raise NotImplementedError

    def get_tool_definition(self, tool_id: int) -> ToolDefinition | None:
        raise NotImplementedError

    def list_tool_definitions(self) -> list[ToolDefinition]:
        raise NotImplementedError

    def assign_tool_to_agent(
        self,
        agent_id: int,
        tool_id: int,
        *,
        enabled: bool = True,
        confirmation_required: bool | None = None,
        read_only: bool | None = None,
    ) -> AgentToolAssignment:
        raise NotImplementedError

    def unassign_tool_from_agent(self, agent_id: int, tool_id: int) -> bool:
        raise NotImplementedError

    def list_agent_tool_assignments(self, agent_id: int) -> list[AgentToolAssignment]:
        raise NotImplementedError

    def list_tools_available_to_agent(self, agent_id: int) -> list[ToolDefinition]:
        raise NotImplementedError

    def execute_tool_call(self, tool_call: ToolCall, *, approval_granted: bool = False) -> ToolResult:
        raise NotImplementedError
