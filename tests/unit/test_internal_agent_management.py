from unittest.mock import MagicMock, patch

import pytest

from apmatia.api.internal import agent_management


class MockAgent:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.name = kwargs.get("name", "Test Agent")
        self.owner_user_id = kwargs.get("owner_user_id", 7)
        self.owner_group_id = kwargs.get("owner_group_id", None)
        self.system_prompt_id = kwargs.get("system_prompt_id", 0)
        self.prompt_id = kwargs.get("prompt_id")
        self.memory_id = kwargs.get("memory_id", 0)
        self.rag_root_ids = kwargs.get("rag_root_ids", [])
        self.tool_ids = kwargs.get("tool_ids", [])
        self.default_model_id = kwargs.get("default_model_id")
        self.active_model_id = kwargs.get("active_model_id")
        self.metadata = kwargs.get("metadata", {})


class TestCreateAgent:
    def test_creates_agent_and_returns_dict(self):
        mock_agent = MockAgent(id=1, name="Test Agent")
        mock_manager = MagicMock()
        mock_manager.create_agent.return_value = mock_agent

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.create_agent("Test Agent")

        mock_manager.create_agent.assert_called_once_with("Test Agent")
        assert result["id"] == 1
        assert result["name"] == "Test Agent"

    def test_creates_agent_with_additional_kwargs(self):
        mock_agent = MockAgent(
            id=1,
            name="Test Agent",
            prompt_id=7,
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300],
            default_model_id=400,
            active_model_id=500,
        )
        mock_manager = MagicMock()
        mock_manager.create_agent.return_value = mock_agent

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.create_agent(
                "Test Agent",
                system_prompt_id=10,
                memory_id=20,
                rag_root_ids=[100, 200],
                tool_ids=[300],
                default_model_id=400,
                active_model_id=500,
            )

        assert result["system_prompt_id"] == 10
        assert result["prompt_id"] == 7
        assert result["memory_id"] == 20
        assert result["rag_root_ids"] == [100, 200]
        assert result["tool_ids"] == [300]
        assert result["default_model_id"] == 400
        assert result["active_model_id"] == 500


class TestGetAgent:
    def test_returns_agent_dict_when_found(self):
        mock_agent = MockAgent(id=1, name="Test Agent")
        mock_manager = MagicMock()
        mock_manager.get_agent.return_value = mock_agent

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.get_agent(1)

        mock_manager.get_agent.assert_called_once_with(1)
        assert result["id"] == 1
        assert result["name"] == "Test Agent"

    def test_returns_none_when_agent_not_found(self):
        mock_manager = MagicMock()
        mock_manager.get_agent.return_value = None

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.get_agent(999)

        assert result is None


class TestUpdateAgent:
    def test_updates_agent_and_returns_dict(self):
        mock_agent = MockAgent(id=1, name="Updated Agent")
        mock_manager = MagicMock()
        mock_manager.update_agent.return_value = mock_agent

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.update_agent(1, name="Updated Agent")

        mock_manager.update_agent.assert_called_once_with(1, name="Updated Agent")
        assert result["name"] == "Updated Agent"

    def test_updates_multiple_fields(self):
        mock_agent = MockAgent(
            id=1,
            name="Updated Agent",
            system_prompt_id=1,
            memory_id=2,
        )
        mock_manager = MagicMock()
        mock_manager.update_agent.return_value = mock_agent

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.update_agent(
                1, name="Updated Agent", system_prompt_id=1, memory_id=2
            )

        assert result["name"] == "Updated Agent"
        assert result["system_prompt_id"] == 1
        assert result["memory_id"] == 2


class TestDeleteAgent:
    def test_deletes_agent_and_returns_true(self):
        mock_manager = MagicMock()
        mock_manager.delete_agent.return_value = True

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.delete_agent(1)

        mock_manager.delete_agent.assert_called_once_with(1)
        assert result is True

    def test_returns_false_when_deletion_fails(self):
        mock_manager = MagicMock()
        mock_manager.delete_agent.return_value = False

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.delete_agent(999)

        assert result is False


class TestListAgents:
    def test_returns_list_of_agent_dicts(self):
        mock_agent1 = MockAgent(id=1, name="Agent 1")
        mock_agent2 = MockAgent(id=2, name="Agent 2")
        mock_manager = MagicMock()
        mock_manager.list_agents.return_value = [mock_agent1, mock_agent2]

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.list_agents()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Agent 1"
        assert result[1]["id"] == 2
        assert result[1]["name"] == "Agent 2"

    def test_returns_empty_list_when_no_agents(self):
        mock_manager = MagicMock()
        mock_manager.list_agents.return_value = []

        with patch("apmatia.api.internal.agent_management.get_agent_manager", return_value=mock_manager):
            result = agent_management.list_agents()

        assert result == []


class TestAgentToDict:
    def test_converts_agent_to_dict_with_all_fields(self):
        mock_agent = MockAgent(
            id=1,
            name="Test Agent",
            owner_user_id=42,
            owner_group_id=9,
            prompt_id=10,
            system_prompt_id=10,
            memory_id=20,
            rag_root_ids=[100, 200],
            tool_ids=[300, 400],
            default_model_id=500,
            active_model_id=600,
            metadata={"key": "value"},
        )

        result = agent_management._agent_to_dict(mock_agent)

        assert result["id"] == 1
        assert result["name"] == "Test Agent"
        assert result["owner_user_id"] == 42
        assert result["owner_group_id"] == 9
        assert result["prompt_id"] == 10
        assert result["system_prompt_id"] == 10
        assert result["memory_id"] == 20
        assert result["rag_root_ids"] == [100, 200]
        assert result["tool_ids"] == [300, 400]
        assert result["default_model_id"] == 500
        assert result["active_model_id"] == 600
        assert result["metadata"] == {"key": "value"}
