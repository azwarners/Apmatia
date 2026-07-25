"""Integration tests for SQLite agent management repositories."""

import tempfile
from pathlib import Path

import pytest

from apmatia.modules.persistence import SQLiteStore

from apmatia.modules.agents.models import Agent
from apmatia.modules.agents.manager import AgentManager
from apmatia.modules.agents.sqlite_repositories import (
    SQLiteAgentRepository,
    AgentManagementTables,
    SQLiteAgentManagementBundle,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    yield path
    import os
    os.close(fd)
    # Clean up
    if Path(path).exists():
        Path(path).unlink()


@pytest.fixture
def store(temp_db):
    """Create a SQLiteStore instance."""
    return SQLiteStore(temp_db)


@pytest.fixture
def tables():
    """Get default table names."""
    return AgentManagementTables()


@pytest.fixture
def agent_repo(store, tables):
    """Create an agent repository."""
    return SQLiteAgentRepository(store, tables)


class TestSQLiteAgentRepository:
    """Integration tests for SQLiteAgentRepository."""

    def test_create_and_get_agent(self, agent_repo):
        """Test creating and retrieving an agent."""
        agent = Agent(
            id=None,
            owner_user_id=101,
            owner_group_id=202,
            mode=0o750,
            name="test_agent",
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0"},
        )
        agent_id = agent_repo.create(agent)

        retrieved = agent_repo.get(agent_id)
        assert retrieved is not None
        assert retrieved.name == "test_agent"
        assert retrieved.owner_user_id == 101
        assert retrieved.owner_group_id == 202
        assert retrieved.mode == 0o750
        assert retrieved.system_prompt_id == 10
        assert retrieved.memory_id == 20
        assert retrieved.rag_root_ids == [100, 200]
        assert retrieved.tool_ids == [300, 400]
        assert retrieved.default_model_id == 50
        assert retrieved.active_model_id == 60
        assert retrieved.metadata == {"version": "1.0"}

    def test_get_by_name(self, agent_repo):
        """Test retrieving an agent by name."""
        agent = Agent(
            id=None,
            name="test_agent",
        )
        agent_id = agent_repo.create(agent)

        retrieved = agent_repo.get_by_name("test_agent")
        assert retrieved is not None
        assert retrieved.id == agent_id

    def test_get_by_name_not_found(self, agent_repo):
        """Test retrieving a non-existent agent by name."""
        retrieved = agent_repo.get_by_name("nonexistent")
        assert retrieved is None

    def test_list_agents(self, agent_repo):
        """Test listing all agents."""
        agent_repo.create(Agent(id=None, name="agent1"))
        agent_repo.create(Agent(id=None, name="agent2"))
        agent_repo.create(Agent(id=None, name="agent3"))

        agents = agent_repo.list_all()
        assert len(agents) == 3

    def test_update_agent(self, agent_repo):
        """Test updating an agent."""
        agent = Agent(
            id=None,
            name="test_agent",
            system_prompt_id=10,
        )
        agent_id = agent_repo.create(agent)

        updated = Agent(
            id=agent_id,
            name="updated_agent",
            system_prompt_id=20,
            memory_id=30,
        )
        agent_repo.update(updated)

        retrieved = agent_repo.get(agent_id)
        assert retrieved.name == "updated_agent"
        assert retrieved.system_prompt_id == 20
        assert retrieved.memory_id == 30

    def test_delete_agent(self, agent_repo):
        """Test deleting an agent."""
        agent = Agent(
            id=None,
            name="test_agent",
        )
        agent_id = agent_repo.create(agent)

        deleted = agent_repo.delete(agent_id)
        assert deleted is True
        assert agent_repo.get(agent_id) is None

    def test_delete_nonexistent_agent(self, agent_repo):
        """Test deleting a non-existent agent."""
        deleted = agent_repo.delete(999)
        assert deleted is False


class TestAgentManagementTables:
    """Tests for AgentManagementTables configuration."""

    def test_default_table_names(self):
        """Test default table names."""
        tables = AgentManagementTables()
        assert tables.agents == "agent_management_agents"

    def test_custom_table_names(self):
        """Test custom table names."""
        tables = AgentManagementTables(
            agents="custom_agents",
        )
        assert tables.agents == "custom_agents"


class TestAgentManagerCloneIntegration:
    """Integration tests for cloning agents through the SQLite bundle."""

    def test_clone_agent_persists_distinct_prompt(self, temp_db):
        sqlite_bundle = SQLiteAgentManagementBundle(temp_db)
        manager = AgentManager(sqlite_bundle.agents, sqlite_bundle.prompts)

        source = manager.create_agent(
            "source_agent",
            owner_user_id=101,
            mode=0o000,
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100],
            tool_ids=[200],
            default_model_id=300,
            active_model_id=400,
            metadata={"role": "source"},
        )
        cloned = manager.clone_agent(source.id, "cloned_agent")

        assert cloned.id is not None
        assert cloned.name == "cloned_agent"
        assert cloned.owner_user_id == 101
        assert cloned.mode == 0o200
        assert cloned.prompt_id is not None
        assert cloned.prompt_id != source.prompt_id
        assert cloned.system_prompt_id == 10
        assert cloned.memory_id == 20
        assert cloned.rag_root_ids == [100]
        assert cloned.tool_ids == [200]
        assert cloned.default_model_id == 300
        assert cloned.active_model_id == 400
        assert cloned.metadata == {"role": "source"}

        retrieved = manager.get_agent(cloned.id)
        assert retrieved is not None
        assert retrieved.name == "cloned_agent"
        assert retrieved.prompt_id == cloned.prompt_id
