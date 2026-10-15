"""Unit tests for surviving tool-management orchestration."""

from dataclasses import replace
import json

import pytest

from apmatia.modules.agents.models import Agent
from apmatia.modules.agents.services import AgentService
from apmatia.modules.agent_tools.models import ToolCall
from apmatia.modules.agent_tools.manager import ToolManager
from apmatia.modules.agent_tools.repositories import AgentToolAssignmentRepository, ToolDefinitionRepository


class InMemoryToolDefinitionRepository(ToolDefinitionRepository):
    def __init__(self):
        self._tools = {}
        self._next_id = 1

    def create(self, tool):
        tool_id = self._next_id
        self._next_id += 1
        self._tools[tool_id] = replace(tool, id=tool_id)
        return tool_id

    def get(self, tool_id):
        return self._tools.get(tool_id)

    def get_by_name(self, name):
        return next((tool for tool in self._tools.values() if tool.name == name), None)

    def get_by_provider_id(self, provider_id):
        return next((tool for tool in self._tools.values() if tool.provider_id == provider_id), None)

    def list_all(self):
        return list(self._tools.values())

    def update(self, tool):
        self._tools[tool.id] = tool


class InMemoryAssignmentRepository(AgentToolAssignmentRepository):
    def __init__(self):
        self._assignments = {}
        self._next_id = 1

    def upsert(self, assignment):
        key = (assignment.agent_id, assignment.tool_id)
        existing = self._assignments.get(key)
        assignment = replace(assignment, id=self._next_id if existing is None else existing.id)
        if existing is None:
            self._next_id += 1
        self._assignments[key] = assignment
        return assignment

    def get(self, assignment_id):
        return next((item for item in self._assignments.values() if item.id == assignment_id), None)

    def get_by_agent_tool(self, agent_id, tool_id):
        return self._assignments.get((agent_id, tool_id))

    def list_by_agent(self, agent_id):
        return [item for (stored_agent_id, _), item in self._assignments.items() if stored_agent_id == agent_id]

    def delete(self, agent_id, tool_id):
        return self._assignments.pop((agent_id, tool_id), None) is not None


class InMemoryAgentService(AgentService):
    def __init__(self):
        self._agents = {1: Agent(id=1, name="Agent One", owner_user_id=1)}

    def create_agent(self, name: str, **kwargs):
        raise NotImplementedError

    def update_agent(self, agent_id: int, **updates):
        updated = replace(self._agents[agent_id], **updates)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: int):
        raise NotImplementedError

    def get_agent(self, agent_id: int):
        return self._agents.get(agent_id)

    def list_agents(self):
        return list(self._agents.values())


@pytest.fixture
def tool_manager():
    return ToolManager(InMemoryToolDefinitionRepository(), InMemoryAssignmentRepository(), InMemoryAgentService())


def test_builtin_tools_are_seeded(tool_manager):
    names = {tool.name for tool in tool_manager.list_tool_definitions()}
    assert {"echo", "get_current_time"} <= names


def test_disabled_tool_cannot_execute(tool_manager):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, tool.id)
    tool_manager.update_tool_definition(tool.id, enabled=False)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={"text": "hello"}))
    assert result.status == "denied"


def test_unassigned_tool_cannot_execute(tool_manager):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={"text": "hello"}))
    assert result.status == "denied"


def test_assigned_enabled_tool_executes(tool_manager):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, tool.id)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={"text": "hello"}))
    assert result.status == "success"
    assert result.result == {"text": "hello"}


def test_input_schema_validation_rejects_bad_arguments(tool_manager):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, tool.id)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={}))
    assert result.status == "invalid_arguments"


def test_confirmation_required_tool_returns_pending(tool_manager):
    tool = tool_manager.create_tool_definition(
        owner_user_id=1,
        name="danger",
        description="Dangerous action",
        input_schema={"type": "object", "additionalProperties": False},
        output_schema={"type": "object"},
        provider_id="missing.provider",
        confirmation_required=True,
        read_only=False,
    )
    tool_manager.assign_tool_to_agent(1, tool.id)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={}))
    assert result.status == "pending_confirmation"


def test_tool_execution_is_audited_to_jsonl(tool_manager, tmp_path, monkeypatch):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, tool.id)
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr("apmatia.modules.agent_tools.audit._audit_path", lambda: audit_path)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={"text": "hello"}))
    assert result.status == "success"
    assert audit_path.exists()
    assert all(json.loads(line) for line in audit_path.read_text().splitlines())


def test_get_current_time_returns_structured_result(tool_manager):
    tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "get_current_time")
    tool_manager.assign_tool_to_agent(1, tool.id)
    result = tool_manager.execute_tool_call(ToolCall(tool_id=tool.id, requester_agent_id=1, arguments={}))
    assert result.status == "success"
    assert "current_time" in result.result
