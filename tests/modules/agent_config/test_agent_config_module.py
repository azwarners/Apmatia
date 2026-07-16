from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.lib.agent_management.models import Agent
from apmatia.modules.agent_config.actions import ACTION_DESCRIPTORS
from apmatia.modules.agent_config.commands import COMMAND_DESCRIPTORS
from apmatia.modules.agent_config.module import APMATIA_AGENT_CONFIG_MODULE, register
from apmatia.modules.agent_config.module_views import ApmatiaAgentConfigModuleViewProvider
from apmatia.modules.agent_config.views import VIEW_DESCRIPTORS


class _AgentManager:
    def __init__(self, agents: list[Agent]):
        self._agents = {int(agent.id or 0): agent for agent in agents}

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def get_agent(self, agent_id: int) -> Agent | None:
        return self._agents.get(agent_id)

    def update_agent(self, agent_id: int, **updates):
        agent = self._agents[agent_id]
        updated = replace(agent, **updates)
        self._agents[agent_id] = updated
        return updated


def test_agent_config_module_registers_agent_config_view():
    registry = Registry()

    register(registry)

    assert registry.list_modules() == [APMATIA_AGENT_CONFIG_MODULE]
    assert [action.action_id for action in registry.list_actions()] == [action.action_id for action in ACTION_DESCRIPTORS]
    assert [command.command_id for command in registry.list_commands()] == [command.command_id for command in COMMAND_DESCRIPTORS]
    assert [view.view_id for view in registry.list_views()] == [view.view_id for view in VIEW_DESCRIPTORS]


def test_agent_config_module_view_provider_updates_agent_roots_with_warnings(tmp_path: Path):
    workspace_root = tmp_path / "workspace" / "planner"
    workspace_root.mkdir(parents=True)
    knowledge_root = tmp_path / "knowledge" / "shared-knowledge"
    manager = _AgentManager(
        [
            Agent(id=1, name="Planner", workspace_root="", knowledge_root=""),
        ]
    )
    provider = ApmatiaAgentConfigModuleViewProvider(agent_manager=manager)

    result = provider.execute_command(
        command=type("Command", (), {"metadata": {"verb": "save"}})(),
        payload={
            "agent_id": 1,
            "workspace_root": str(workspace_root),
            "knowledge_root": str(knowledge_root),
        },
        context=ModuleViewContext(),
    )

    assert result is not None
    assert result["status"] == "updated"
    assert result["item"]["workspace_root"] == str(workspace_root)
    assert result["item"]["knowledge_root"] == str(knowledge_root)
    assert any("knowledge root" in warning.lower() for warning in result["warnings"])
