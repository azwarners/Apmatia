from dataclasses import replace
from unittest.mock import patch

from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.apmatia_administration.tooling import (
    ApmatiaAdministrationToolProvider,
    apmatia_administration_tool_definitions,
    build_apmatia_administration_tool_providers,
)


class InMemoryAgentService(AgentService):
    def __init__(self):
        self._agents = {1: Agent(id=1, name="Caller", owner_user_id=99, owner_group_id=12, mode=0o640)}
        self._prompts = {}
        self._next_agent_id = 2
        self._next_prompt_id = 7

    def create_agent(self, name: str, **kwargs):
        prompt_id = kwargs.get("prompt_id")
        prompt_payload = {key: kwargs[key] for key in kwargs if key in {
            "personality",
            "skills",
            "purpose",
            "backstory",
            "communication_style",
            "operating_principles",
            "autonomy_level",
            "decision_making_style",
            "memory_policy",
            "domain_priorities",
            "relationship_to_user",
            "tool_use_policy",
            "capability_boundaries",
            "output_preferences",
            "safety_ethics",
            "selfhood_truthfulness",
            "conflict_resolution_rules",
            "use_raw_prompt_override",
            "raw_prompt_override",
        }}
        if prompt_id is None and prompt_payload:
            prompt_id = self._next_prompt_id
            self._next_prompt_id += 1
            self._prompts[prompt_id] = prompt_payload
        agent = Agent(
            id=self._next_agent_id,
            name=name,
            prompt_id=prompt_id,
            owner_user_id=kwargs.get("owner_user_id"),
            owner_group_id=kwargs.get("owner_group_id"),
            mode=kwargs.get("mode", 0o600),
            memory_id=kwargs.get("memory_id", 0),
            rag_root_ids=kwargs.get("rag_root_ids", []),
            tool_ids=kwargs.get("tool_ids", []),
            default_model_id=kwargs.get("default_model_id"),
            active_model_id=kwargs.get("active_model_id"),
            metadata=kwargs.get("metadata", {}),
        )
        self._agents[self._next_agent_id] = agent
        self._next_agent_id += 1
        return agent

    def clone_agent(self, source_agent_id: int, name: str, **kwargs):
        source = self._agents[source_agent_id]
        prompt_id = source.prompt_id
        if prompt_id is not None and prompt_id in self._prompts:
            prompt_id = self._next_prompt_id
            self._next_prompt_id += 1
            self._prompts[prompt_id] = dict(self._prompts[source.prompt_id])
        return self.create_agent(
            name,
            prompt_id=prompt_id,
            owner_user_id=kwargs.get("owner_user_id", source.owner_user_id),
            owner_group_id=kwargs.get("owner_group_id", source.owner_group_id),
            mode=kwargs.get("mode", source.mode | 0o200),
            system_prompt_id=kwargs.get("system_prompt_id", source.system_prompt_id),
            memory_id=kwargs.get("memory_id", source.memory_id),
            rag_root_ids=list(kwargs.get("rag_root_ids", source.rag_root_ids)),
            tool_ids=list(kwargs.get("tool_ids", source.tool_ids)),
            default_model_id=kwargs.get("default_model_id", source.default_model_id),
            active_model_id=kwargs.get("active_model_id", source.active_model_id),
            metadata=kwargs.get("metadata", dict(source.metadata)),
        )

    def update_agent(self, agent_id: int, **updates):
        updated = replace(self._agents[agent_id], **updates)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: int):
        return self._agents.pop(agent_id, None) is not None

    def get_agent(self, agent_id: int):
        return self._agents.get(agent_id)

    def list_agents(self):
        return list(self._agents.values())

    def get_prompt(self, prompt_id: int):
        payload = self._prompts.get(prompt_id)
        if payload is None:
            return None
        from apmatia.lib.agent_management.agent_prompt import AgentPrompt

        return AgentPrompt(**payload)


def test_admin_tool_definition_includes_prompt_fields():
    definitions = apmatia_administration_tool_definitions()
    definition = definitions[0]

    assert definition["name"] == "apmatia_create_agent"
    assert "personality" in definition["input_schema"]["properties"]
    assert "raw_prompt_override" in definition["input_schema"]["properties"]
    assert definitions[1]["name"] == "clone_agent_as"
    assert "source_agent_id" in definitions[1]["input_schema"]["properties"]
    assert definitions[2]["name"] == "set_agent_mode"
    assert definitions[2]["input_schema"]["properties"]["mode"]["enum"] == ["discussion", "agentic"]


def test_admin_tool_provider_creates_agent_with_prompt_fields():
    agent_service = InMemoryAgentService()
    provider = ApmatiaAdministrationToolProvider(
        provider_id="builtin.apmatia_create_agent",
        action="create_agent",
        agent_service=agent_service,
    )

    result = provider.execute(
        {
            "name": "Welcome Agent",
            "purpose": "Help people build things in Apmatia.",
            "personality": "Warm and encouraging.",
        },
        tool_call=type("ToolCall", (), {"requester_agent_id": 1})(),
    )

    assert result["agent"]["name"] == "Welcome Agent"
    assert result["agent"]["prompt_id"] is not None
    assert result["agent"]["owner_user_id"] == 99
    assert result["agent"]["owner_group_id"] == 12
    assert result["agent"]["mode"] == 0o640


def test_admin_tool_provider_promotes_read_only_caller_mode_for_new_agents():
    agent_service = InMemoryAgentService()
    agent_service._agents[1] = replace(agent_service._agents[1], mode=0o400)
    provider = ApmatiaAdministrationToolProvider(
        provider_id="builtin.apmatia_create_agent",
        action="create_agent",
        agent_service=agent_service,
    )

    result = provider.execute(
        {
            "name": "Writable Child",
        },
        tool_call=type("ToolCall", (), {"requester_agent_id": 1})(),
    )

    assert result["agent"]["name"] == "Writable Child"
    assert result["agent"]["mode"] == 0o600


def test_admin_tool_provider_clones_agent_as_new_name():
    agent_service = InMemoryAgentService()
    provider = ApmatiaAdministrationToolProvider(
        provider_id="builtin.apmatia_clone_agent_as",
        action="clone_agent",
        agent_service=agent_service,
    )

    result = provider.execute(
        {
            "source_agent_id": 1,
            "name": "Caller Clone",
        },
        tool_call=type("ToolCall", (), {"requester_agent_id": 1})(),
    )

    assert result["agent"]["name"] == "Caller Clone"
    assert result["agent"]["owner_user_id"] == 99
    assert result["agent"]["owner_group_id"] == 12
    assert result["agent"]["mode"] == 0o640
    assert result["agent"]["id"] == 2


def test_admin_tool_provider_inherits_owner_context_from_discussion_when_caller_is_ownerless():
    agent_service = InMemoryAgentService()
    agent_service._agents[1] = Agent(id=1, name="Caller", owner_user_id=None, owner_group_id=None)
    provider = ApmatiaAdministrationToolProvider(
        provider_id="builtin.apmatia_create_agent",
        action="create_agent",
        agent_service=agent_service,
    )

    class MockDiscussion:
        owner_user_id = 77
        owner_group_id = 88
        group_id = 91

    with patch("apmatia.lib.discussions.discussion_state._get_discussion", return_value=MockDiscussion()):
        result = provider.execute(
            {
                "name": "Discussion Agent",
            },
            tool_call=type("ToolCall", (), {"requester_agent_id": 1, "discussion_id": "disc-1"})(),
        )

    assert result["agent"]["owner_user_id"] == 77
    assert result["agent"]["owner_group_id"] == 88


def test_admin_tool_provider_factory_returns_builtin_provider():
    providers = build_apmatia_administration_tool_providers(InMemoryAgentService())

    assert len(providers) == 3
    assert providers[0].provider_id == "builtin.apmatia_create_agent"
    assert providers[1].provider_id == "builtin.apmatia_clone_agent_as"
    assert providers[2].provider_id == "builtin.apmatia_set_agent_mode"


def test_admin_tool_provider_switches_agent_mode():
    agent_service = InMemoryAgentService()
    provider = ApmatiaAdministrationToolProvider(
        provider_id="builtin.apmatia_set_agent_mode",
        action="set_agent_mode",
        agent_service=agent_service,
    )

    with patch("apmatia.lib.discussions.discussion_state") as mock_discussion_state:
        mock_discussion_state.set_agent_mode.return_value = {
            "previous_mode": "discussion",
            "current_mode": "agentic",
            "status": "updated",
        }
        result = provider.execute(
            {"mode": "agentic"},
            tool_call=type("ToolCall", (), {"requester_agent_id": 1, "discussion_id": "disc-1"})(),
        )

    assert result == {
        "previous_mode": "discussion",
        "current_mode": "agentic",
        "status": "updated",
    }
    mock_discussion_state.set_agent_mode.assert_called_once_with(discussion_id="disc-1", mode="agentic")
