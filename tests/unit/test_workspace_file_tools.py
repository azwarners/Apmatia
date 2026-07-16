from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from apmatia.core import tool_management_runtime
from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management import (
    ToolCall,
    ToolManager,
    build_workspace_file_tool_providers,
    workspace_file_tool_definitions,
)
from apmatia.lib.tool_management.repositories import AgentToolAssignmentRepository, ToolDefinitionRepository


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
    def __init__(self, workspace_root: Path):
        self._agents = {
            1: Agent(id=1, name="Agent One", owner_user_id=1, workspace_root=str(workspace_root / "agent-1"))
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
def workspace_tool_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    workspace_root = tmp_path / "workspace" / "agents"
    (workspace_root / "agent-1").mkdir(parents=True, exist_ok=True)
    agent_service = InMemoryAgentService(workspace_root)
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_workspace_file_tool_providers(agent_service, base_dir=tmp_path),
        builtin_definitions=workspace_file_tool_definitions(),
    )


def _assign_tool(manager: ToolManager, agent_id: int, tool_name: str) -> int:
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == tool_name)
    manager.assign_tool_to_agent(agent_id, int(tool.id))
    return int(tool.id)


def test_workspace_file_tools_are_registered_and_discoverable(workspace_tool_manager: ToolManager):
    names = {tool.name for tool in workspace_tool_manager.list_tool_definitions()}

    assert {
        "workspace_list_files",
        "workspace_read_file",
        "workspace_write_file",
        "workspace_delete_file",
    } <= names


def test_workspace_file_tools_can_list_read_write_and_delete(tmp_path: Path, workspace_tool_manager: ToolManager):
    workspace_root = tmp_path / "workspace" / "agents" / "agent-1"
    (workspace_root / "notes").mkdir(parents=True, exist_ok=True)
    (workspace_root / "notes" / "todo.txt").write_text("hello\n", encoding="utf-8")

    list_tool_id = _assign_tool(workspace_tool_manager, 1, "workspace_list_files")
    list_result = workspace_tool_manager.execute_tool_call(
        ToolCall(tool_id=list_tool_id, requester_agent_id=1, arguments={})
    )
    assert list_result.status == "success"
    assert list_result.result["workspace_root"] == str(workspace_root)
    assert "notes/todo.txt" in {item["relative_path"] for item in list_result.result["files"]}

    read_tool_id = _assign_tool(workspace_tool_manager, 1, "workspace_read_file")
    read_result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=read_tool_id,
            requester_agent_id=1,
            arguments={"relative_path": "notes/todo.txt"},
        )
    )
    assert read_result.status == "success"
    assert read_result.result["content"] == "hello\n"

    write_tool_id = _assign_tool(workspace_tool_manager, 1, "workspace_write_file")
    write_result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=write_tool_id,
            requester_agent_id=1,
            arguments={"relative_path": "notes/plan.txt", "content": "plan\n"},
        )
    )
    assert write_result.status == "success"
    assert write_result.result["created"] is True
    assert (workspace_root / "notes" / "plan.txt").read_text(encoding="utf-8") == "plan\n"

    delete_tool_id = _assign_tool(workspace_tool_manager, 1, "workspace_delete_file")
    delete_result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=delete_tool_id,
            requester_agent_id=1,
            arguments={"relative_path": "notes/plan.txt"},
        )
    )
    assert delete_result.status == "success"
    assert delete_result.result["deleted"] is True
    assert not (workspace_root / "notes" / "plan.txt").exists()


def test_workspace_file_tools_auto_create_missing_app_workspace_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / ".apmatia"))

    app_workspace_root = tmp_path / ".apmatia" / "workspace" / "HR"

    class _AgentService(AgentService):
        def __init__(self) -> None:
            self._agent = Agent(id=1, name="HR", owner_user_id=1, workspace_root=str(app_workspace_root), tool_ids=())

        def create_agent(self, name: str, **kwargs):
            raise NotImplementedError

        def clone_agent(self, source_agent_id: int, name: str, **kwargs):
            raise NotImplementedError

        def update_agent(self, agent_id: int, **updates):
            self._agent = replace(self._agent, **updates)
            return self._agent

        def delete_agent(self, agent_id: int):
            raise NotImplementedError

        def get_agent(self, agent_id: int):
            return self._agent if agent_id == 1 else None

        def list_agents(self):
            return [self._agent]

    agent_service = _AgentService()
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_workspace_file_tool_providers(agent_service),
        builtin_definitions=workspace_file_tool_definitions(),
    )
    list_tool_id = _assign_tool(tool_manager, 1, "workspace_list_files")

    result = tool_manager.execute_tool_call(ToolCall(tool_id=list_tool_id, requester_agent_id=1, arguments={}))

    assert result.status == "success"
    assert result.result["workspace_root"] == str(app_workspace_root)
    assert app_workspace_root.exists()
    assert result.result["count"] == 0


def test_workspace_file_tools_reject_unsafe_paths(workspace_tool_manager: ToolManager, tmp_path: Path):
    workspace_root = tmp_path / "workspace" / "agents" / "agent-1"
    tool_id = _assign_tool(workspace_tool_manager, 1, "workspace_write_file")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={"relative_path": "../outside.txt", "content": "x"},
        )
    )

    assert result.status == "error"
    assert result.error["code"] == "WORKSPACE_PATH_ERROR"


def test_workspace_file_tools_import_without_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from apmatia.lib.tool_management.workspace_files import workspace_file_tool_definitions
assert workspace_file_tool_definitions()
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr


def test_runtime_seeds_workspace_file_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / ".apmatia"))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    import apmatia.core.tool_management_runtime as runtime

    importlib.reload(runtime)
    names = {tool.name for tool in runtime.get_tool_manager().list_tool_definitions()}

    assert "workspace_list_files" in names
    assert "workspace_read_file" in names
    assert "workspace_write_file" in names
    assert "workspace_delete_file" in names
