from __future__ import annotations

import pytest

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.modules.agents.commands import COMMAND_DESCRIPTORS
from apmatia.modules.agents.manager import AgentManager
from apmatia.modules.agents.module_views import AgentsModuleViewProvider
from apmatia.modules.agents.sqlite_repositories import SQLiteAgentManagementBundle
from apmatia.modules.agents.starter_catalog import install_starter_profiles, load_starter_profiles


def _manager(tmp_path) -> AgentManager:
    tmp_path.mkdir(parents=True, exist_ok=True)
    bundle = SQLiteAgentManagementBundle(tmp_path / "agents.db")
    return AgentManager(bundle.agents, bundle.prompts)


def test_bundled_profiles_have_unique_ids_and_complete_apmatia_prompts():
    profiles = load_starter_profiles()

    assert len(profiles) >= 5
    assert len({profile["profile_id"] for profile in profiles}) == len(profiles)
    assert {"luna"} <= {profile["name"].split()[0].casefold() for profile in profiles}
    assert all(profile["specialization"].strip() for profile in profiles)
    assert all(profile["prompt"]["personality"].strip() for profile in profiles)
    assert all("Persistent memory is disabled" in profile["prompt"]["memory_policy"] for profile in profiles)
    assert all("No Apmatia tools are enabled" in profile["prompt"]["tool_use_policy"] for profile in profiles)


def test_install_is_idempotent_and_reapplication_preserves_customizations(tmp_path):
    manager = _manager(tmp_path)
    first = install_starter_profiles(manager, owner_user_id=17, default_model_id=42)
    luna = next(agent for agent in manager.list_agents() if agent.name == "Luna the Linux Admin")
    manager.update_prompt(luna.prompt_id, personality="My customized Luna.")
    manager.update_agent(luna.id, name="Luna at Home", default_model_id=99, is_public=True)

    second = install_starter_profiles(manager, owner_user_id=17, default_model_id=43, publish=True)
    saved_luna = manager.get_agent(luna.id)

    assert first["installed"] == 5
    assert second["installed"] == 0
    assert second["already_installed"] == 5
    assert saved_luna is not None
    assert saved_luna.name == "Luna at Home"
    assert saved_luna.default_model_id == 99
    assert saved_luna.is_public is True
    assert manager.get_prompt(saved_luna.prompt_id).personality == "My customized Luna."
    assert {agent.default_model_id for agent in manager.list_agents()} == {42, 99}


def test_install_defaults_private_and_can_publish_new_profiles_intentionally(tmp_path):
    private_manager = _manager(tmp_path / "private")
    install_starter_profiles(private_manager, owner_user_id=3)
    assert all(not agent.is_public for agent in private_manager.list_agents())
    assert all(agent.default_model_id is None for agent in private_manager.list_agents())

    public_manager = _manager(tmp_path / "public")
    result = install_starter_profiles(public_manager, owner_user_id=4, publish=True)
    assert result["published"] is True
    assert all(agent.is_public for agent in public_manager.list_agents())


def test_existing_name_conflict_is_reported_without_overwrite(tmp_path):
    manager = _manager(tmp_path)
    original = manager.create_agent("Mira the Software Engineer", owner_user_id=22)

    result = install_starter_profiles(manager, owner_user_id=23)

    assert result["name_conflicts"] == 1
    conflict = next(profile for profile in result["profiles"] if profile["status"] == "name_conflict")
    assert conflict["profile_id"] == "apmatia.starter.software-engineer.v1"
    assert manager.get_agent(original.id).starter_profile_id is None


def test_existing_agents_command_installs_profiles_for_authenticated_user(tmp_path):
    manager = _manager(tmp_path)
    provider = AgentsModuleViewProvider(manager_factory=lambda: manager)
    command = next(command for command in COMMAND_DESCRIPTORS if command.command_id == "agents.install_starters")

    with pytest.raises(ValueError, match="Authentication required"):
        provider.execute_command(
            command=command,
            payload={},
            context=ModuleViewContext(user_id=None, group_ids=frozenset()),
        )
    result = provider.execute_command(
        command=command,
        payload={"default_model_id": "73"},
        context=ModuleViewContext(user_id=31, group_ids=frozenset()),
    )

    assert result["installed"] == 5
    assert all(agent.owner_user_id == 31 for agent in manager.list_agents())
    assert {agent.default_model_id for agent in manager.list_agents()} == {73}
