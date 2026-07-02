from __future__ import annotations

from typing import Protocol

from .models import AgentToolAssignment, ToolDefinition


class ToolDefinitionRepository(Protocol):
    def create(self, tool: ToolDefinition) -> int:
        raise NotImplementedError

    def get(self, tool_id: int) -> ToolDefinition | None:
        raise NotImplementedError

    def get_by_name(self, name: str) -> ToolDefinition | None:
        raise NotImplementedError

    def get_by_provider_id(self, provider_id: str) -> ToolDefinition | None:
        raise NotImplementedError

    def list_all(self) -> list[ToolDefinition]:
        raise NotImplementedError

    def update(self, tool: ToolDefinition) -> None:
        raise NotImplementedError


class AgentToolAssignmentRepository(Protocol):
    def upsert(self, assignment: AgentToolAssignment) -> AgentToolAssignment:
        raise NotImplementedError

    def get(self, assignment_id: int) -> AgentToolAssignment | None:
        raise NotImplementedError

    def get_by_agent_tool(self, agent_id: int, tool_id: int) -> AgentToolAssignment | None:
        raise NotImplementedError

    def list_by_agent(self, agent_id: int) -> list[AgentToolAssignment]:
        raise NotImplementedError

    def delete(self, agent_id: int, tool_id: int) -> bool:
        raise NotImplementedError
