"""Unit tests for SQLite repositories."""

import tempfile

import pytest

from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.sqlite_repositories import (
    SQLiteAgentRepository,
    SQLiteAgentManagementBundle,
    AgentManagementTables,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name


@pytest.fixture
def tables():
    """Default table names."""
    return AgentManagementTables()


@pytest.fixture
def agent_repo(temp_db_path, tables):
    """Create SQLiteAgentRepository instance."""
    try:
        from persistence import SQLiteStore
    except ModuleNotFoundError:
        from apmatia.lib.persistence.persistence import SQLiteStore
    store = SQLiteStore(temp_db_path)
    return SQLiteAgentRepository(store, tables)


class TestSQLiteAgentRepository:
    """Tests for SQLiteAgentRepository."""

    def test_create_agent(self, agent_repo):
        """Test creating an agent."""
        agent = Agent(
            id=None,
            owner_user_id=11,
            owner_group_id=12,
            mode=0o754,
            name="TestAgent",
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0"},
        )
        agent_id = agent_repo.create(agent)
        assert agent_id is not None
        assert agent_id > 0

    def test_get_agent(self, agent_repo):
        """Test getting an agent by id."""
        agent = Agent(
            id=None,
            name="TestAgent",
            system_prompt_id=10,
            memory_id=20,
        )
        agent_id = agent_repo.create(agent)
        retrieved = agent_repo.get(agent_id)
        assert retrieved is not None
        assert retrieved.name == "TestAgent"
        assert retrieved.system_prompt_id == 10
        assert retrieved.memory_id == 20

    def test_get_agent_not_found(self, agent_repo):
        """Test getting a non-existent agent."""
        result = agent_repo.get(999)
        assert result is None

    def test_get_by_name(self, agent_repo):
        """Test getting an agent by name."""
        agent = Agent(
            id=None,
            name="TestAgent",
        )
        agent_repo.create(agent)
        retrieved = agent_repo.get_by_name("TestAgent")
        assert retrieved is not None
        assert retrieved.name == "TestAgent"

    def test_get_by_name_not_found(self, agent_repo):
        """Test getting a non-existent agent by name."""
        result = agent_repo.get_by_name("NonExistent")
        assert result is None

    def test_list_agents_empty(self, agent_repo):
        """Test listing agents when empty."""
        agents = agent_repo.list_all()
        assert agents == []

    def test_list_agents_multiple(self, agent_repo):
        """Test listing multiple agents."""
        agent1 = Agent(
            id=None,
            name="Agent1",
        )
        agent2 = Agent(
            id=None,
            name="Agent2",
        )
        agent_repo.create(agent1)
        agent_repo.create(agent2)
        agents = agent_repo.list_all()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"Agent1", "Agent2"}

    def test_update_agent(self, agent_repo):
        """Test updating an agent."""
        agent = Agent(
            id=None,
            name="TestAgent",
            system_prompt_id=10,
        )
        agent_id = agent_repo.create(agent)
        agent = agent_repo.get(agent_id)
        updated_agent = Agent(
            id=agent.id,
            name="UpdatedAgent",
            system_prompt_id=20,
            memory_id=30,
            rag_root_ids=[100],
            tool_ids=[200],
            default_model_id=40,
            active_model_id=41,
            metadata={"updated": True},
        )
        agent_repo.update(updated_agent)
        updated = agent_repo.get(agent_id)
        assert updated.name == "UpdatedAgent"
        assert updated.system_prompt_id == 20
        assert updated.memory_id == 30

    def test_update_agent_not_found(self, agent_repo):
        """Test updating a non-existent agent."""
        agent = Agent(
            id=999,
            name="TestAgent",
        )
        with pytest.raises(ValueError):
            agent_repo.update(agent)

    def test_delete_agent(self, agent_repo):
        """Test deleting an agent."""
        agent = Agent(
            id=None,
            name="TestAgent",
        )
        agent_id = agent_repo.create(agent)
        result = agent_repo.delete(agent_id)
        assert result is True
        assert agent_repo.get(agent_id) is None

    def test_delete_agent_not_found(self, agent_repo):
        """Test deleting a non-existent agent."""
        result = agent_repo.delete(999)
        assert result is False

    def test_agent_with_full_config(self, agent_repo):
        """Test creating an agent with full configuration."""
        agent = Agent(
            id=None,
            name="FullAgent",
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0", "env": "test"},
        )
        agent_id = agent_repo.create(agent)
        retrieved = agent_repo.get(agent_id)
        assert retrieved.system_prompt_id == 10
        assert retrieved.memory_id == 20
        assert retrieved.rag_root_ids == [100, 200]
        assert retrieved.tool_ids == [300, 400]
        assert retrieved.default_model_id == 50
        assert retrieved.active_model_id == 60
        assert retrieved.metadata == {"version": "1.0", "env": "test"}

    def test_get_agent_normalizes_missing_base_fields(self, agent_repo):
        agent_repo._store.insert(
            agent_repo._tables.agents,
            {
                "name": "LegacyAgent",
                "system_prompt_id": 10,
                "memory_id": 20,
                "rag_root_ids": "[]",
                "tool_ids": "[]",
                "metadata": "{}",
            },
        )

        retrieved = agent_repo.get_by_name("LegacyAgent")

        assert retrieved is not None
        assert retrieved.owner_user_id is None
        assert retrieved.owner_group_id is None
        assert retrieved.mode == 0
        assert retrieved.created_at.tzinfo is not None
        assert retrieved.updated_at.tzinfo is not None


class TestSQLiteAgentManagementBundle:
    """Tests for SQLiteAgentManagementBundle."""

    def test_bundle_creates_agent_repository(self, temp_db_path):
        """Test that bundle creates agent repository."""
        bundle = SQLiteAgentManagementBundle(temp_db_path)
        assert bundle.agents is not None

    def test_bundle_persistence(self, temp_db_path):
        """Test that bundle persists data across instances."""
        # First instance
        bundle1 = SQLiteAgentManagementBundle(temp_db_path)
        agent = Agent(
            id=None,
            name="TestAgent",
        )
        agent_id = bundle1.agents.create(agent)

        # Second instance (new connection)
        bundle2 = SQLiteAgentManagementBundle(temp_db_path)
        retrieved = bundle2.agents.get(agent_id)
        assert retrieved is not None
        assert retrieved.name == "TestAgent"

    def test_bundle_custom_tables(self, temp_db_path):
        """Test bundle with custom table names."""
        custom_tables = AgentManagementTables(
            agents="custom_agents",
        )
        bundle = SQLiteAgentManagementBundle(temp_db_path, custom_tables)
        agent = Agent(
            id=None,
            name="TestAgent",
        )
        agent_id = bundle.agents.create(agent)
        retrieved = bundle.agents.get(agent_id)
        assert retrieved is not None
        assert retrieved.name == "TestAgent"
