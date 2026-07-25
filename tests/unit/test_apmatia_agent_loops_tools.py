from __future__ import annotations

from dataclasses import replace

from apmatia.modules.agents.models import Agent
from apmatia.modules.agents.services import AgentService
from apmatia.modules.agent_tools import ToolCall, ToolManager
from apmatia.modules.agent_tools.models import ToolDefinition
from apmatia.modules.agent_tools.repositories import AgentToolAssignmentRepository, ToolDefinitionRepository
from apmatia.modules.agent_loops.tools import agent_loop_tool_definitions, build_agent_loop_tool_providers


class InMemoryToolDefinitionRepository(ToolDefinitionRepository):
    def __init__(self) -> None:
        self._tools: dict[int, ToolDefinition] = {}
        self._next_id = 1

    def create(self, tool: ToolDefinition) -> int:
        tool_id = self._next_id
        self._next_id += 1
        self._tools[tool_id] = replace(tool, id=tool_id)
        return tool_id

    def get(self, tool_id: int) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> ToolDefinition | None:
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def get_by_provider_id(self, provider_id: str) -> ToolDefinition | None:
        for tool in self._tools.values():
            if tool.provider_id == provider_id:
                return tool
        return None

    def list_all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def update(self, tool: ToolDefinition) -> None:
        self._tools[int(tool.id or 0)] = tool


class InMemoryAssignmentRepository(AgentToolAssignmentRepository):
    def __init__(self) -> None:
        self._assignments: dict[tuple[int, int], object] = {}

    def upsert(self, assignment):
        self._assignments[(assignment.agent_id, assignment.tool_id)] = assignment
        return assignment

    def get(self, assignment_id):
        for assignment in self._assignments.values():
            if assignment.id == assignment_id:
                return assignment
        return None

    def get_by_agent_tool(self, agent_id, tool_id):
        return self._assignments.get((agent_id, tool_id))

    def list_by_agent(self, agent_id):
        return [assignment for (stored_agent_id, _), assignment in self._assignments.items() if stored_agent_id == agent_id]

    def delete(self, agent_id, tool_id):
        return self._assignments.pop((agent_id, tool_id), None) is not None


class InMemoryAgentService(AgentService):
    def __init__(self) -> None:
        self._agents = {
            1: Agent(id=1, name="Ada", owner_user_id=1, owner_group_id=None, tool_ids=[]),
            2: Agent(id=2, name="Bea", owner_user_id=1, owner_group_id=None, tool_ids=[]),
            3: Agent(id=3, name="Avery", owner_user_id=1, owner_group_id=None, tool_ids=[]),
        }

    def create_agent(self, name: str, **kwargs):
        raise NotImplementedError

    def clone_agent(self, source_agent_id: int, name: str, **kwargs):
        raise NotImplementedError

    def update_agent(self, agent_id: int, **updates):
        agent = self._agents[agent_id]
        updated = replace(agent, **updates)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: int):
        raise NotImplementedError

    def get_agent(self, agent_id: int):
        return self._agents.get(agent_id)

    def list_agents(self):
        return list(self._agents.values())


def _build_manager() -> ToolManager:
    agent_service = InMemoryAgentService()
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_agent_loop_tool_providers(agent_service),
        builtin_definitions=agent_loop_tool_definitions(),
    )


def test_list_agents_tool_is_registered_and_available_without_assignment():
    manager = _build_manager()
    tools = {tool.name for tool in manager.list_tool_definitions()}

    assert "list_agents" in tools
    assert "list_agents" in {tool.name for tool in manager.list_tools_available_to_agent(1)}


def test_list_agents_tool_returns_all_agents():
    manager = _build_manager()
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == "list_agents")

    result = manager.execute_tool_call(
        ToolCall(
            tool_id=int(tool.id or 0),
            requester_agent_id=1,
            arguments={},
            discussion_id="disc-1",
        )
    )

    assert result.status == "success"
    assert [agent["name"] for agent in result.result["agents"]] == ["Ada", "Bea", "Avery"]


def test_list_agents_tool_filters_by_name_contains():
    manager = _build_manager()
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == "list_agents")

    result = manager.execute_tool_call(
        ToolCall(
            tool_id=int(tool.id or 0),
            requester_agent_id=1,
            arguments={"name_contains": "av"},
            discussion_id="disc-1",
        )
    )

    assert result.status == "success"
    assert [agent["name"] for agent in result.result["agents"]] == ["Avery"]
