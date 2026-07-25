from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from apmatia.core.modules import create_module_scaffold
from apmatia.core import tool_management_runtime
from apmatia.modules.agents.models import Agent
from apmatia.modules.agents.services import AgentService
from apmatia.modules.agent_tools import (
    ToolCall,
    ToolManager,
    build_workspace_module_tool_providers,
    workspace_module_tool_definitions,
)
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
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace" / "modules"))
    (tmp_path / "workspace" / "modules").mkdir(parents=True, exist_ok=True)
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        InMemoryAgentService(),
        builtin_providers=build_workspace_module_tool_providers(base_dir=tmp_path),
        builtin_definitions=workspace_module_tool_definitions(),
    )


def _assign_tool(manager: ToolManager, agent_id: int, tool_name: str) -> int:
    tool = next(tool for tool in manager.list_tool_definitions() if tool.name == tool_name)
    manager.assign_tool_to_agent(agent_id, int(tool.id))
    return int(tool.id)


def test_workspace_tools_are_registered_and_discoverable(workspace_tool_manager: ToolManager):
    names = {tool.name for tool in workspace_tool_manager.list_tool_definitions()}

    assert {
        "plan_workspace_module",
        "create_workspace_module",
        "list_workspace_module_files",
        "read_workspace_module_file",
        "write_workspace_module_file",
        "validate_workspace_module",
    } <= names


def test_plan_workspace_module_returns_plan_and_writes_no_files(workspace_tool_manager: ToolManager, tmp_path: Path):
    tool_id = _assign_tool(workspace_tool_manager, 1, "plan_workspace_module")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={"module_slug": "productivity", "display_name": "Productivity"},
        )
    )

    assert result.status == "success"
    assert result.result["module_path"].endswith("workspace/modules/productivity")
    assert result.result["passed"] is True
    assert not (tmp_path / "workspace/modules/productivity").exists()


def test_create_workspace_module_creates_draft_module(workspace_tool_manager: ToolManager, tmp_path: Path):
    tool_id = _assign_tool(workspace_tool_manager, 1, "create_workspace_module")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={
                "module_slug": "productivity",
                "display_name": "Productivity",
                "description": "Tasks and notes.",
                "author": "Nick Warner",
            },
        )
    )

    assert result.status == "success"
    assert (tmp_path / "workspace/modules/productivity/module.py").exists()
    assert (tmp_path / "src/modules/productivity").exists() is False
    assert result.result["module_dir"].endswith("workspace/modules/productivity")


def test_create_workspace_module_fails_when_workspace_root_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "missing-workspace" / "modules"))
    manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        InMemoryAgentService(),
        builtin_providers=build_workspace_module_tool_providers(base_dir=tmp_path),
        builtin_definitions=workspace_module_tool_definitions(),
    )
    tool_id = _assign_tool(manager, 1, "create_workspace_module")

    result = manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={"module_slug": "productivity", "display_name": "Productivity"},
        )
    )

    assert result.status == "error"
    assert result.error["code"] == "MISSING_WORKSPACE_DIRECTORY"
    assert result.error["request_id"] == result.call_id


def test_list_workspace_module_files_lists_scaffold_files(workspace_tool_manager: ToolManager, tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    tool_id = _assign_tool(workspace_tool_manager, 1, "list_workspace_module_files")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"module_slug": "productivity"})
    )

    assert result.status == "success"
    assert result.result["module_path"].endswith("workspace/modules/productivity")
    relative_paths = {item["relative_path"] for item in result.result["files"]}
    assert "module.py" in relative_paths
    assert "manifest.toml" in relative_paths


def test_read_workspace_module_file_reads_content(workspace_tool_manager: ToolManager, tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    (tmp_path / "workspace/modules/productivity/notes.txt").write_text("hello\n", encoding="utf-8")
    tool_id = _assign_tool(workspace_tool_manager, 1, "read_workspace_module_file")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={"module_slug": "productivity", "relative_path": "notes.txt"},
        )
    )

    assert result.status == "success"
    assert result.result["content"] == "hello\n"


def test_write_workspace_module_file_writes_only_inside_workspace(workspace_tool_manager: ToolManager, tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    tool_id = _assign_tool(workspace_tool_manager, 1, "write_workspace_module_file")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={
                "module_slug": "productivity",
                "relative_path": "actions.py",
                "content": "VALUE = 1\n",
            },
        )
    )

    assert result.status == "success"
    assert (tmp_path / "workspace/modules/productivity/actions.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (tmp_path / "src/modules/productivity/actions.py").exists()


def test_write_workspace_module_file_rejects_unsafe_path(workspace_tool_manager: ToolManager, tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    tool_id = _assign_tool(workspace_tool_manager, 1, "write_workspace_module_file")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            requester_agent_id=1,
            arguments={
                "module_slug": "productivity",
                "relative_path": "../outside.py",
                "content": "VALUE = 1\n",
            },
        )
    )

    assert result.status == "error"
    assert result.error["code"] == "WORKSPACE_PATH_ERROR"
    assert ".." in result.error["message"]


def test_validate_workspace_module_returns_structured_validation_results(workspace_tool_manager: ToolManager, tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    tool_id = _assign_tool(workspace_tool_manager, 1, "validate_workspace_module")
    result = workspace_tool_manager.execute_tool_call(
        ToolCall(tool_id=tool_id, requester_agent_id=1, arguments={"module_slug": "productivity"})
    )

    assert result.status == "success"
    assert result.result["module_slug"] == "productivity"
    assert result.result["passed"] is True
    assert result.result["manifest"]["module_id"] == "productivity"
    assert result.result["manifest"]["status"] == "development"
    assert result.result["manifest"]["category"] == "feature"
    assert result.result["manifest"]["default_enabled"] is True
    assert result.result["manifest"]["tags"] == []
    assert result.result["manifest"]["metadata"] == {}
    assert result.result["manifest"]["dependencies"] == {
        "python": "",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }


def test_workspace_tools_import_without_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from apmatia.modules.agent_tools.workspace_modules import workspace_module_tool_definitions
assert workspace_module_tool_definitions()
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr


def test_runtime_seeds_workspace_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / ".apmatia"))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    import apmatia.core.tool_management_runtime as runtime

    importlib.reload(runtime)
    monkeypatch.setattr(runtime, "get_config_value", lambda *args, **kwargs: True)
    runtime.get_tool_manager()
    names = {tool.name for tool in runtime.get_tool_manager().list_tool_definitions()}

    assert "plan_workspace_module" in names
    assert "create_workspace_module" in names
    assert "write_workspace_module_file" in names
    assert "apmatia_os_admin" in names
