from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.modules.dev_tools.tooling import (
    build_dev_tools_tool_providers,
    dev_tools_tool_definitions,
)
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
        self._agents = {
            1: Agent(
                id=1,
                name="Agent One",
                owner_user_id=1,
                workspace_root="",
                knowledge_root="",
            )
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


@pytest.fixture
def source_tool_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    agent_service = InMemoryAgentService()
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_dev_tools_tool_providers(agent_service, base_dir=tmp_path),
        builtin_definitions=dev_tools_tool_definitions(),
    )


def _assign_tool(manager: ToolManager, agent_id: int, tool_name: str) -> int:
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == tool_name)
    manager.assign_tool_to_agent(agent_id, int(tool.id))
    return int(tool.id)


def test_dev_tools_are_registered(source_tool_manager: ToolManager):
    names = {tool.name for tool in source_tool_manager.list_tool_definitions()}

    assert {"apmatia_tree", "apmatia_read", "apmatia_trace_import"} <= names


def test_tree_filters_noise_and_marks_special_files(source_tool_manager: ToolManager, tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "project").mkdir()
    (root / "project" / "src").mkdir()
    (root / "project" / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "project" / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "project" / "src" / "cli.py").write_text("print('cli')\n", encoding="utf-8")
    (root / "project" / "src" / "module.py").write_text("value = 1\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / "venv").mkdir()
    (root / "__pycache__").mkdir()
    source_tool_manager._agent_service._agents[1] = Agent(
        id=1,
        name="Agent One",
        owner_user_id=1,
        workspace_root=str(root / "project"),
        knowledge_root=str(tmp_path / "knowledge"),
    )
    (tmp_path / "knowledge").mkdir()

    tool_id = _assign_tool(source_tool_manager, 1, "apmatia_tree")
    result = source_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"root_dir": ".", "depth": 2})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["root_dir"] == str(root / "project")
    assert result.result["repo_root"] == str(root / "project")
    assert result.result["counts"]["files"] == 4
    child_kinds = {child["name"]: child["kind"] for child in result.result["tree"]["children"]}
    assert child_kinds["src"] == "directory"
    src_children = {child["name"]: child["kind"] for child in result.result["tree"]["children"][0]["children"]}
    assert src_children["__init__.py"] == "package_init"
    assert src_children["main.py"] == "entry_point"
    assert src_children["cli.py"] == "entry_point"
    assert "venv" not in child_kinds
    assert "__pycache__" not in child_kinds


def test_read_file_truncates_middle_section_and_reports_metadata(source_tool_manager: ToolManager, tmp_path: Path):
    workspace = tmp_path / "workspace"
    knowledge = tmp_path / "knowledge"
    workspace.mkdir()
    knowledge.mkdir()
    source_tool_manager._agent_service._agents[1] = Agent(
        id=1,
        name="Agent One",
        owner_user_id=1,
        workspace_root=str(workspace),
        knowledge_root=str(knowledge),
    )
    source = workspace / "long.py"
    lines = [f"line {index}\n" for index in range(1, 1002)]
    source.write_text("".join(lines), encoding="utf-8")

    tool_id = _assign_tool(source_tool_manager, 1, "apmatia_read")
    result = source_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"file_path": str(source)})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["line_count"] == 1001
    assert result.result["file_size"] == source.stat().st_size
    assert result.result["truncated"] is True
    assert result.result["file_path"] == str(source)
    assert result.result["repo_root"] == str(workspace)
    assert "line 1" in result.result["content"]
    assert "line 1001" in result.result["content"]
    assert "[truncated 901 middle lines]" in result.result["content"]


def test_trace_import_classifies_dependencies_and_reports_cycles(source_tool_manager: ToolManager, tmp_path: Path):
    workspace = tmp_path / "workspace"
    knowledge = tmp_path / "knowledge"
    workspace.mkdir()
    knowledge.mkdir()
    source_tool_manager._agent_service._agents[1] = Agent(
        id=1,
        name="Agent One",
        owner_user_id=1,
        workspace_root=str(workspace),
        knowledge_root=str(knowledge),
    )
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("import json\nfrom .b import helper\n", encoding="utf-8")
    (pkg / "b.py").write_text("from .a import helper as other_helper\n", encoding="utf-8")

    tool_id = _assign_tool(source_tool_manager, 1, "apmatia_trace_import")
    result = source_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"module_path": str(pkg / "a.py")})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    classifications = {item["classification"] for item in result.result["dependencies"]}
    assert "Standard Library" in classifications
    assert "Local" in classifications
    assert result.result["cycles"]
    cycle = result.result["cycles"][0]
    assert str(pkg / "a.py") in cycle
    assert str(pkg / "b.py") in cycle


def test_tools_can_read_from_knowledge_root(source_tool_manager: ToolManager, tmp_path: Path):
    workspace = tmp_path / "workspace"
    knowledge = tmp_path / "knowledge"
    workspace.mkdir()
    knowledge.mkdir()
    source_tool_manager._agent_service._agents[1] = Agent(
        id=1,
        name="Agent One",
        owner_user_id=1,
        workspace_root=str(workspace),
        knowledge_root=str(knowledge),
    )
    note = knowledge / "facts.md"
    note.write_text("knowledge base\n", encoding="utf-8")

    tool_id = _assign_tool(source_tool_manager, 1, "apmatia_read")
    result = source_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"file_path": "facts.md"})
    )

    assert result.status == "success"
    assert result.result["ok"] is True
    assert result.result["file_path"] == str(note)
    assert result.result["repo_root"] == str(knowledge)


def test_tools_reject_paths_outside_agent_roots(source_tool_manager: ToolManager, tmp_path: Path):
    workspace = tmp_path / "workspace"
    knowledge = tmp_path / "knowledge"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    knowledge.mkdir()
    outside.write_text("nope\n", encoding="utf-8")
    source_tool_manager._agent_service._agents[1] = Agent(
        id=1,
        name="Agent One",
        owner_user_id=1,
        workspace_root=str(workspace),
        knowledge_root=str(knowledge),
    )

    tool_id = _assign_tool(source_tool_manager, 1, "apmatia_read")
    result = source_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"file_path": str(outside)})
    )

    assert result.status == "success"
    assert result.result["ok"] is False
    assert result.result["error"]["code"] == "DEV_TOOLS_ERROR"
