from __future__ import annotations

from dataclasses import replace
from typing import Any

from apmatia.modules.agents.services import AgentService
from apmatia.lib.apmatia_core.models import utc_now

from .executor import ToolExecutor
from .models import AgentToolAssignment, ToolCall, ToolDefinition, ToolResult
from .registry import ToolProvider, ToolRegistry, builtin_tool_definitions, register_builtin_tools
from .repositories import AgentToolAssignmentRepository, ToolDefinitionRepository
from .services import ToolService


class ToolManager(ToolService):
    def __init__(
        self,
        tool_repo: ToolDefinitionRepository,
        assignment_repo: AgentToolAssignmentRepository,
        agent_service: AgentService,
        registry: ToolRegistry | None = None,
        builtin_providers: list[ToolProvider] | None = None,
        builtin_definitions: list[dict[str, Any]] | None = None,
        include_builtin_tools: bool = True,
    ) -> None:
        self._tool_repo = tool_repo
        self._assignment_repo = assignment_repo
        self._agent_service = agent_service
        self._registry = registry or ToolRegistry()
        self._builtin_definitions = builtin_definitions or []
        self._include_builtin_tools = include_builtin_tools
        if include_builtin_tools:
            register_builtin_tools(self._registry, providers=builtin_providers)
        else:
            for provider in builtin_providers or []:
                self._registry.register(provider)
        self._executor = ToolExecutor(tool_repo, assignment_repo, agent_service, self._registry)
        self.ensure_builtin_tools()

    def ensure_builtin_tools(self) -> None:
        definitions = (
            builtin_tool_definitions(extra_definitions=self._builtin_definitions)
            if self._include_builtin_tools
            else self._builtin_definitions
        )
        for payload in definitions:
            existing = self._tool_repo.get_by_provider_id(payload["provider_id"])
            if existing is None:
                self.create_tool_definition(**payload)

    def create_tool_definition(self, **kwargs: Any) -> ToolDefinition:
        name = self._validate_tool_name(str(kwargs.get("name", "")).strip())
        provider_id = self._validate_provider_id(str(kwargs.get("provider_id", "")).strip())
        self._ensure_unique_tool_name(name)

        tool = ToolDefinition(
            id=None,
            owner_user_id=kwargs.get("owner_user_id"),
            owner_group_id=kwargs.get("owner_group_id"),
            mode=kwargs.get("mode", 0o000),
            name=name,
            description=str(kwargs.get("description", "")),
            input_schema=dict(kwargs.get("input_schema", {})),
            output_schema=kwargs.get("output_schema"),
            provider_id=provider_id,
            enabled=bool(kwargs.get("enabled", True)),
            confirmation_required=bool(kwargs.get("confirmation_required", False)),
            read_only=bool(kwargs.get("read_only", True)),
            metadata=dict(kwargs.get("metadata", {})),
        )
        tool_id = self._tool_repo.create(tool)
        return replace(tool, id=tool_id)

    def get_tool_definition(self, tool_id: int) -> ToolDefinition | None:
        return self._tool_repo.get(tool_id)

    def list_tool_definitions(self) -> list[ToolDefinition]:
        return self._tool_repo.list_all()

    def assign_tool_to_agent(
        self,
        agent_id: int,
        tool_id: int,
        *,
        enabled: bool = True,
        confirmation_required: bool | None = None,
        read_only: bool | None = None,
    ) -> AgentToolAssignment:
        agent = self._agent_service.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        if self._tool_repo.get(tool_id) is None:
            raise ValueError(f"Tool not found: {tool_id}")

        assignment = self._assignment_repo.upsert(
            AgentToolAssignment(
                agent_id=agent_id,
                tool_id=tool_id,
                enabled=enabled,
                confirmation_required=confirmation_required,
                read_only=read_only,
            )
        )
        if tool_id not in agent.tool_ids:
            self._agent_service.update_agent(agent_id, tool_ids=[*agent.tool_ids, tool_id])
        return assignment

    def unassign_tool_from_agent(self, agent_id: int, tool_id: int) -> bool:
        agent = self._agent_service.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        deleted = self._assignment_repo.delete(agent_id, tool_id)
        if tool_id in agent.tool_ids:
            updated_tool_ids = [existing_tool_id for existing_tool_id in agent.tool_ids if existing_tool_id != tool_id]
            self._agent_service.update_agent(agent_id, tool_ids=updated_tool_ids)
            deleted = True
        return deleted

    def list_agent_tool_assignments(self, agent_id: int) -> list[AgentToolAssignment]:
        agent = self._agent_service.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        return self._assignment_repo.list_by_agent(agent_id)

    def list_tools_available_to_agent(self, agent_id: int) -> list[ToolDefinition]:
        agent = self._agent_service.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        tool_ids = {tool.id for tool in self._tool_repo.list_all() if tool.id is not None}
        tool_ids.update(agent.tool_ids)
        tool_ids.update(assignment.tool_id for assignment in self._assignment_repo.list_by_agent(agent_id))

        available: list[ToolDefinition] = []
        for tool_id in sorted(tool_id for tool_id in tool_ids if tool_id is not None):
            access = self._executor.resolve_tool_access(agent_id, int(tool_id))
            if access is not None:
                available.append(access.tool)
        return available

    def execute_tool_call(self, tool_call: ToolCall, *, approval_granted: bool = False) -> ToolResult:
        return self._executor.execute(tool_call, approval_granted=approval_granted)

    def update_tool_definition(self, tool_id: int, **updates: Any) -> ToolDefinition:
        tool = self._tool_repo.get(tool_id)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_id}")
        name = self._validate_tool_name(str(updates.get("name", tool.name)).strip())
        provider_id = self._validate_provider_id(str(updates.get("provider_id", tool.provider_id)).strip())
        self._ensure_unique_tool_name(name, exclude_tool_id=tool_id)
        updated = replace(
            tool,
            name=name,
            description=updates.get("description", tool.description),
            input_schema=updates.get("input_schema", tool.input_schema),
            output_schema=updates.get("output_schema", tool.output_schema),
            provider_id=provider_id,
            enabled=updates.get("enabled", tool.enabled),
            confirmation_required=updates.get("confirmation_required", tool.confirmation_required),
            read_only=updates.get("read_only", tool.read_only),
            metadata=updates.get("metadata", tool.metadata),
            updated_at=utc_now(),
        )
        self._tool_repo.update(updated)
        return updated

    @staticmethod
    def _validate_tool_name(name: str) -> str:
        if not name:
            raise ValueError("Tool name cannot be empty.")
        return name

    @staticmethod
    def _validate_provider_id(provider_id: str) -> str:
        if not provider_id:
            raise ValueError("Tool provider_id cannot be empty.")
        return provider_id

    def _ensure_unique_tool_name(self, name: str, exclude_tool_id: int | None = None) -> None:
        existing = self._tool_repo.get_by_name(name)
        if existing is None:
            return
        if exclude_tool_id is not None and existing.id == exclude_tool_id:
            return
        raise ValueError(f"Tool already exists: {name}")
