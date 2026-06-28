from unittest.mock import MagicMock, patch

from src.api.internal import tools as internal_tools


class MockTool:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.owner_user_id = kwargs.get("owner_user_id")
        self.owner_group_id = kwargs.get("owner_group_id")
        self.mode = kwargs.get("mode", 0)
        self.name = kwargs.get("name", "echo")
        self.description = kwargs.get("description", "Echo tool")
        self.input_schema = kwargs.get("input_schema", {"type": "object"})
        self.output_schema = kwargs.get("output_schema", {"type": "object"})
        self.provider_id = kwargs.get("provider_id", "builtin.echo")
        self.enabled = kwargs.get("enabled", True)
        self.confirmation_required = kwargs.get("confirmation_required", False)
        self.read_only = kwargs.get("read_only", True)
        self.metadata = kwargs.get("metadata", {})
        self.created_at = kwargs.get("created_at", MagicMock())
        self.updated_at = kwargs.get("updated_at", MagicMock())
        self.created_at.isoformat.return_value = "2026-06-22T00:00:00+00:00"
        self.updated_at.isoformat.return_value = "2026-06-22T00:00:00+00:00"


class MockAssignment:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.agent_id = kwargs.get("agent_id", 7)
        self.tool_id = kwargs.get("tool_id", 1)
        self.enabled = kwargs.get("enabled", True)
        self.confirmation_required = kwargs.get("confirmation_required")
        self.read_only = kwargs.get("read_only")


def test_list_tool_definitions_serializes_manager_results():
    mock_manager = MagicMock()
    mock_manager.list_tool_definitions.return_value = [MockTool(id=1, name="echo")]

    with patch("src.api.internal.tools.get_tool_manager", return_value=mock_manager):
        result = internal_tools.list_tool_definitions()

    assert result[0]["id"] == 1
    assert result[0]["name"] == "echo"
    assert result[0]["provider_id"] == "builtin.echo"


def test_assign_tool_to_agent_returns_assignment_dict():
    mock_manager = MagicMock()
    mock_manager.assign_tool_to_agent.return_value = MockAssignment(id=3, agent_id=7, tool_id=2)

    with patch("src.api.internal.tools.get_tool_manager", return_value=mock_manager):
        result = internal_tools.assign_tool_to_agent(7, 2, enabled=True)

    mock_manager.assign_tool_to_agent.assert_called_once_with(
        7,
        2,
        enabled=True,
        confirmation_required=None,
        read_only=None,
    )
    assert result == {
        "id": 3,
        "agent_id": 7,
        "tool_id": 2,
        "enabled": True,
        "confirmation_required": None,
        "read_only": None,
    }


def test_execute_tool_call_returns_structured_result():
    mock_manager = MagicMock()
    mock_manager.execute_tool_call.return_value = MagicMock(
        call_id="call_123",
        status="success",
        result={"text": "hi"},
        error=None,
        metadata={"tool_id": 1},
    )

    with patch("src.api.internal.tools.get_tool_manager", return_value=mock_manager):
        result = internal_tools.execute_tool_call(
            tool_id=1,
            arguments={"text": "hi"},
            requester_agent_id=7,
            approval_granted=True,
        )

    assert result == {
        "call_id": "call_123",
        "status": "success",
        "result": {"text": "hi"},
        "error": None,
        "metadata": {"tool_id": 1},
    }


def test_update_tool_definition_returns_serialized_tool():
    mock_manager = MagicMock()
    mock_manager.update_tool_definition.return_value = MockTool(id=2, name="echo", enabled=False)

    with patch("src.api.internal.tools.get_tool_manager", return_value=mock_manager):
        result = internal_tools.update_tool_definition(2, enabled=False)

    mock_manager.update_tool_definition.assert_called_once_with(2, enabled=False)
    assert result["id"] == 2
    assert result["enabled"] is False
