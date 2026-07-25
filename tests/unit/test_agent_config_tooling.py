from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.modules.agent_config.tooling import build_agent_config_tool_providers, agent_config_tool_definitions
from apmatia.modules.agent_tools import ToolCall, ToolManager
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
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def get_by_provider_id(self, provider_id):
        for tool in self._tools.values():
            if tool.provider_id == provider_id:
                return tool
        return None

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
        if existing is None:
            assignment = replace(assignment, id=self._next_id)
            self._next_id += 1
        else:
            assignment = replace(assignment, id=existing.id)
        self._assignments[key] = assignment
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
    def __init__(self):
        self._agents = {1: Agent(id=1, name="Agent One", owner_user_id=1)}

    def create_agent(self, name: str, **kwargs):
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


@pytest.fixture
def agent_config_tool_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir(parents=True)
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        InMemoryAgentService(),
        builtin_providers=build_agent_config_tool_providers(base_dir=tmp_path),
        builtin_definitions=agent_config_tool_definitions(),
    )


def _assign_tool(manager: ToolManager, agent_id: int, tool_name: str) -> int:
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == tool_name)
    manager.assign_tool_to_agent(agent_id, int(tool.id))
    return int(tool.id)


def test_agent_config_tools_are_registered(agent_config_tool_manager: ToolManager):
    names = {tool.name for tool in agent_config_tool_manager.list_tool_definitions()}

    assert {"agent_config_readme_first", "agent_config_tree", "agent_config_read"} <= names


def test_agent_config_readme_first_returns_root_and_usage(agent_config_tool_manager: ToolManager, tmp_path: Path):
    tool_id = _assign_tool(agent_config_tool_manager, 1, "agent_config_readme_first")
    result = agent_config_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["base_dir"] == str(tmp_path)
    assert result.result["knowledge_root"] == str(tmp_path / "knowledge")
    assert "/knowledge" in result.result["root_aliases"]
    assert any(tool["name"] == "agent_config_read" for tool in result.result["tools"])
    assert any(example["tool"] == "agent_config_read" for example in result.result["examples"])


def test_agent_config_tree_can_filter_files_and_respect_depth(
    agent_config_tool_manager: ToolManager,
    tmp_path: Path,
):
    root = tmp_path / "knowledge"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "topic").mkdir()
    (docs / "topic" / "nested").mkdir()
    (docs / "topic" / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (root / "root-note.txt").write_text("root\n", encoding="utf-8")

    tool_id = _assign_tool(agent_config_tool_manager, 1, "agent_config_tree")
    result = agent_config_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={
                "path": "/knowledge/docs/sub/../topic",
                "depth": 1,
                "mode": "directories",
            },
        )
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["base_dir"] == str(tmp_path)
    assert result.result["relative_path"] == "docs/topic"
    assert result.result["normalized_path"] == "docs/topic"
    assert result.result["mode"] == "directories"
    assert result.result["tree"]["name"] == "topic"
    assert [child["name"] for child in result.result["tree"]["children"]] == ["nested"]
    assert result.result["tree"]["children"][0]["children"] == []
    assert result.result["tree"]["children"][0]["truncated"] is True


def test_agent_config_read_returns_text_and_metadata(
    agent_config_tool_manager: ToolManager,
    tmp_path: Path,
):
    root = tmp_path / "knowledge"
    root.mkdir(parents=True, exist_ok=True)
    content = "line 1\nline 2\n"
    file_path = root / "note.txt"
    file_path.write_text(content, encoding="utf-8")

    tool_id = _assign_tool(agent_config_tool_manager, 1, "agent_config_read")
    result = agent_config_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"file_path": "/knowledge/note.txt"})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["base_dir"] == str(tmp_path)
    assert result.result["file_path"] == str(file_path)
    assert result.result["relative_path"] == "note.txt"
    assert result.result["normalized_path"] == "note.txt"
    assert result.result["line_count"] == 2
    assert result.result["file_size"] == file_path.stat().st_size
    assert result.result["content"] == content


def test_agent_config_tools_reject_path_escape(
    agent_config_tool_manager: ToolManager,
):
    tool_id = _assign_tool(agent_config_tool_manager, 1, "agent_config_read")
    result = agent_config_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"file_path": "../outside.txt"})
    )

    assert result.status == "success"
    assert result.result["ok"] is False
    assert result.result["error"]["code"] == "KNOWLEDGE_ERROR"
    assert "relative to the knowledge root" in result.result["error"]["message"]
