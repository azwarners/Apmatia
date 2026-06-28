"""Unit tests for agent management models."""

import pytest
from datetime import datetime, timezone

from src.lib.apmatia_core.models import ApmatiaObject
from src.lib.agent_management.models import Agent


class TestAgent:
    """Tests for Agent dataclass."""

    def test_create_agent_minimal(self):
        agent = Agent(
            id=1,
            name="test_agent",
        )
        assert isinstance(agent, ApmatiaObject)
        assert agent.id == 1
        assert agent.name == "test_agent"
        assert agent.prompt_id is None
        assert agent.system_prompt_id == 0
        assert agent.memory_id == 0
        assert agent.rag_root_ids == []
        assert agent.tool_ids == []
        assert agent.default_model_id is None
        assert agent.active_model_id is None
        assert agent.metadata == {}

    def test_create_agent_full(self):
        agent = Agent(
            id=1,
            owner_user_id=7,
            owner_group_id=8,
            mode=0o640,
            name="test_agent",
            prompt_id=5,
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=50,
            active_model_id=60,
            metadata={"version": "1.0"},
        )
        assert agent.id == 1
        assert agent.owner_user_id == 7
        assert agent.owner_group_id == 8
        assert agent.mode == 0o640
        assert agent.name == "test_agent"
        assert agent.prompt_id == 5
        assert agent.system_prompt_id == 10
        assert agent.memory_id == 20
        assert agent.rag_root_ids == [100, 200]
        assert agent.tool_ids == [300, 400]
        assert agent.default_model_id == 50
        assert agent.active_model_id == 60
        assert agent.metadata == {"version": "1.0"}

    def test_agent_default_values(self):
        agent = Agent(id=None, name="test")
        assert agent.system_prompt_id == 0
        assert agent.memory_id == 0
        assert agent.rag_root_ids == []
        assert agent.tool_ids == []
        assert agent.default_model_id is None
        assert agent.active_model_id is None
        assert agent.metadata == {}

    def test_agent_equality(self):
        timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        agent1 = Agent(id=1, name="test", created_at=timestamp, updated_at=timestamp)
        agent2 = Agent(id=1, name="test", created_at=timestamp, updated_at=timestamp)
        assert agent1 == agent2

    def test_agent_inequality(self):
        agent1 = Agent(id=1, name="test1")
        agent2 = Agent(id=2, name="test2")
        assert agent1 != agent2
