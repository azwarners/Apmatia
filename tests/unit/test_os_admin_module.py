from __future__ import annotations

import importlib

import pytest

from apmatia.core.registry import Registry
from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management.models import ToolDefinition
from apmatia.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle
from apmatia.modules.os_admin.module import APMATIA_OS_ADMIN_MODULE, register
from apmatia.modules.os_admin.tooling import (
    os_admin_tool_definitions,
)


class InMemoryAgentService(AgentService):
    def __init__(self) -> None:
        self.agent = Agent(id=1, name="Test", description="", mode=0o777)

    def create_agent(self, name: str, **kwargs) -> Agent:
        raise NotImplementedError

    def clone_agent(self, source_agent_id: int, name: str, **kwargs) -> Agent:
        raise NotImplementedError

    def get_agent(self, agent_id: int) -> Agent | None:
        return self.agent if agent_id == 1 else None

    def list_agents(self) -> list[Agent]:
        return [self.agent]

    def update_agent(self, agent_id: int, **updates):
        for key, value in updates.items():
            setattr(self.agent, key, value)
        return self.agent

    def delete_agent(self, agent_id: int) -> bool:
        raise NotImplementedError


def test_os_admin_module_registers_development_metadata_and_tool():
    registry = Registry()

    register(registry)

    assert APMATIA_OS_ADMIN_MODULE.status.value == "development"
    assert APMATIA_OS_ADMIN_MODULE.category.value == "infrastructure"
    assert [module.module_id for module in registry.list_modules(include_development=True)] == ["os_admin"]
    assert [tool.tool_id for tool in registry.list_tools()] == ["apmatia_os_admin"]


def test_os_admin_definition_uses_module_metadata():
    definition = os_admin_tool_definitions()[0]

    assert definition["name"] == "apmatia_os_admin"
    assert definition["provider_id"] == "builtin.apmatia_os_admin"
    assert definition["metadata"]["module"] == "os_admin"
    assert "library" not in definition["metadata"]


def test_runtime_only_seeds_os_admin_when_development_modules_are_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / ".apmatia"))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    import apmatia.core.tool_management_runtime as runtime

    importlib.reload(runtime)
    monkeypatch.setattr(runtime, "get_config_value", lambda *args, **kwargs: False)
    stable_names = {tool.name for tool in runtime.get_tool_manager().list_tool_definitions()}
    assert "apmatia_os_admin" not in stable_names

    monkeypatch.setattr(runtime, "get_config_value", lambda *args, **kwargs: True)
    development_names = {tool.name for tool in runtime.get_tool_manager().list_tool_definitions()}
    assert "apmatia_os_admin" in development_names


def test_runtime_migrates_persisted_system_audit_definition(tmp_path):
    import apmatia.core.tool_management_runtime as runtime

    bundle = SQLiteToolManagementBundle(tmp_path / "tools.db")
    old_id = bundle.tools.create(
        ToolDefinition(
            name="apmatia_system_audit",
            description="Old system audit tool.",
            provider_id="builtin.apmatia_system_audit",
            enabled=True,
            metadata={"builtin": True, "library": "system_audit"},
        )
    )

    runtime._migrate_os_admin_tool_definition(bundle.tools, development_enabled=False)

    assert bundle.tools.get_by_provider_id("builtin.apmatia_system_audit") is None
    migrated = bundle.tools.get_by_provider_id("builtin.apmatia_os_admin")
    assert migrated is not None
    assert migrated.id == old_id
    assert migrated.name == "apmatia_os_admin"
    assert migrated.enabled is False
    assert migrated.metadata["module"] == "os_admin"
    assert "library" not in migrated.metadata
