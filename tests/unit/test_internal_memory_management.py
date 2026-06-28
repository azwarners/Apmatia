from unittest.mock import MagicMock, patch

from src.api.internal import memory_management as internal_memory


class MockMemory:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.title = kwargs.get("title", "Note")
        self.content = kwargs.get("content", "Remember this")
        self.tags = kwargs.get("tags", ["alpha"])
        self.owner_user_id = kwargs.get("owner_user_id", 7)
        self.owner_group_id = kwargs.get("owner_group_id")
        self.owner_agent_id = kwargs.get("owner_agent_id", 11)
        self.mode = kwargs.get("mode", 0)
        self.created_by_agent_id = kwargs.get("created_by_agent_id", 3)
        self.source_discussion_id = kwargs.get("source_discussion_id", "disc-1")
        self.source_message_ids = kwargs.get("source_message_ids", ["1"])
        self.visibility = kwargs.get("visibility", "draft")
        self.status = kwargs.get("status", "active")
        self.created_at = kwargs.get("created_at", MagicMock())
        self.updated_at = kwargs.get("updated_at", MagicMock())
        self.created_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"
        self.updated_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"


def test_list_memories_serializes_manager_results():
    mock_manager = MagicMock()
    mock_manager.list_memories.return_value = [MockMemory(id=4, title="Saved")]

    with patch("src.api.internal.memory_management.get_memory_manager", return_value=mock_manager):
        result = internal_memory.list_memories()

    assert result[0]["id"] == 4
    assert result[0]["title"] == "Saved"
    assert result[0]["owner_agent_id"] == 11
    assert result[0]["status"] == "active"
    assert result[0]["created_at"] == "2026-06-23T00:00:00+00:00"


def test_archive_memory_returns_serialized_memory():
    mock_manager = MagicMock()
    mock_manager.archive_memory.return_value = MockMemory(id=8, status="archived")

    with patch("src.api.internal.memory_management.get_memory_manager", return_value=mock_manager):
        result = internal_memory.archive_memory(8, requester_user_id=7)

    mock_manager.archive_memory.assert_called_once_with(8, requester_user_id=7)
    assert result["id"] == 8
    assert result["status"] == "archived"
