"""Unit tests for agent management module (AgentManager)."""

from unittest.mock import MagicMock

import pytest

from apmatia.lib.agent_management.module import AgentManager
from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.repositories import AgentRepository
from apmatia.lib.agent_management.agent_prompt import default_agent_prompt
from apmatia.lib.agent_management.prompt_repositories import AgentPromptRepository


class MockAgentRepository(AgentRepository):
    """Mock implementation of AgentRepository for testing."""

    def __init__(self):
        self._agents = {}
        self._next_id = 1

    def create(self, agent: Agent) -> int:
        agent_id = self._next_id
        self._next_id += 1
        agent_with_id = Agent(
            id=agent_id,
            owner_user_id=agent.owner_user_id,
            owner_group_id=agent.owner_group_id,
            mode=agent.mode,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            name=agent.name,
            prompt_id=agent.prompt_id,
            system_prompt_id=agent.system_prompt_id,
            memory_id=agent.memory_id,
            rag_root_ids=agent.rag_root_ids,
            tool_ids=agent.tool_ids,
            default_model_id=agent.default_model_id,
            active_model_id=agent.active_model_id,
            metadata=agent.metadata,
        )
        self._agents[agent_id] = agent_with_id
        return agent_id

    def get(self, agent_id: int) -> Agent | None:
        return self._agents.get(agent_id)

    def get_by_name(self, name: str) -> Agent | None:
        for agent in self._agents.values():
            if agent.name == name:
                return agent
        return None

    def list_all(self) -> list[Agent]:
        return list(self._agents.values())

    def update(self, agent: Agent) -> None:
        if agent.id not in self._agents:
            raise ValueError(f"Agent {agent.id} not found")
        self._agents[agent.id] = agent

    def delete(self, agent_id: int) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False


class TestAgentManager:
    """Tests for AgentManager class."""

    @pytest.fixture
    def agent_manager(self):
        agent_repo = MockAgentRepository()
        prompt_repo = MagicMock(spec=AgentPromptRepository)
        prompt_repo.create.side_effect = range(1, 100)
        prompt_repo.get.return_value = default_agent_prompt()
        return AgentManager(agent_repo, prompt_repo)

    def test_create_agent(self, agent_manager):
        """Test creating a new agent."""
        agent = agent_manager.create_agent("test_agent")

        assert agent.name == "test_agent"
        assert agent.mode == 0o600
        assert agent.prompt_id == 1
        assert agent.system_prompt_id == 0
        assert agent.memory_id == 0
        assert agent.rag_root_ids == []
        assert agent.tool_ids == []
        assert agent.default_model_id is None
        assert agent.active_model_id is None
        assert agent.workspace_root.endswith("agents/agent-1")
        assert agent.metadata == {}
        assert agent.id is not None

    def test_create_agent_with_all_fields(self, agent_manager):
        """Test creating an agent with all fields."""
        agent = agent_manager.create_agent(
            "test_agent",
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0"},
        )

        assert agent.name == "test_agent"
        assert agent.system_prompt_id == 10
        assert agent.memory_id == 20
        assert agent.rag_root_ids == [100, 200]
        assert agent.tool_ids == [300, 400]
        assert agent.default_model_id == 50
        assert agent.active_model_id == 60
        assert agent.metadata == {"version": "1.0"}

    def test_clone_agent_copies_source_configuration_and_unlocks_owner_write(self, agent_manager):
        source = agent_manager.create_agent(
            "source_agent",
            owner_user_id=7,
            mode=0o000,
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0"},
        )

        cloned = agent_manager.clone_agent(source.id, "cloned_agent")

        assert cloned.id is not None
        assert cloned.name == "cloned_agent"
        assert cloned.owner_user_id == 7
        assert cloned.mode == 0o200
        assert cloned.prompt_id != source.prompt_id
        assert cloned.system_prompt_id == 10
        assert cloned.memory_id == 20
        assert cloned.rag_root_ids == [100, 200]
        assert cloned.tool_ids == [300, 400]
        assert cloned.default_model_id == 50
        assert cloned.active_model_id == 60
        assert cloned.workspace_root.endswith(f"agents/agent-{cloned.id}")
        assert cloned.metadata == {"version": "1.0"}

    def test_create_agent_empty_name(self, agent_manager):
        """Test creating an agent with empty name."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            agent_manager.create_agent("   ")

    def test_create_agent_duplicate_name(self, agent_manager):
        """Test creating an agent with duplicate name."""
        agent_manager.create_agent("test_agent")
        with pytest.raises(ValueError, match="Agent already exists"):
            agent_manager.create_agent("test_agent")

    def test_get_agent(self, agent_manager):
        """Test getting an agent by ID."""
        agent = agent_manager.create_agent("test_agent")
        retrieved = agent_manager.get_agent(agent.id)

        assert retrieved is not None
        assert retrieved.name == "test_agent"

    def test_get_agent_not_found(self, agent_manager):
        """Test getting a non-existent agent."""
        agent = agent_manager.get_agent(999)
        assert agent is None

    def test_list_agents_empty(self, agent_manager):
        """Test listing agents when none exist."""
        agents = agent_manager.list_agents()
        assert agents == []

    def test_list_agents_multiple(self, agent_manager):
        """Test listing multiple agents."""
        agent_manager.create_agent("agent1")
        agent_manager.create_agent("agent2")
        agent_manager.create_agent("agent3")

        agents = agent_manager.list_agents()
        assert len(agents) == 3

    def test_update_agent(self, agent_manager):
        """Test updating an agent."""
        agent = agent_manager.create_agent("test_agent")
        updated = agent_manager.update_agent(
            agent.id,
            name="updated_agent",
            system_prompt_id=10,
            memory_id=20,
        )

        assert updated.name == "updated_agent"
        assert updated.system_prompt_id == 10
        assert updated.memory_id == 20

    def test_get_agent_system_prompt(self, agent_manager):
        agent = agent_manager.create_agent("test_agent")
        prompt = agent_manager.get_agent_system_prompt(agent.id)
        assert "You are test_agent." in prompt

    def test_update_agent_not_found(self, agent_manager):
        """Test updating a non-existent agent."""
        with pytest.raises(ValueError, match="Agent not found"):
            agent_manager.update_agent(999, name="New")

    def test_delete_agent(self, agent_manager):
        """Test deleting an agent."""
        agent = agent_manager.create_agent("test_agent")
        result = agent_manager.delete_agent(agent.id)

        assert result is True
        assert agent_manager.get_agent(agent.id) is None

    def test_delete_agent_not_found(self, agent_manager):
        """Test deleting a non-existent agent."""
        result = agent_manager.delete_agent(999)
        assert result is False
