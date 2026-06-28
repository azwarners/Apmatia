from unittest.mock import MagicMock, patch

from src.api.internal import wiki_management as internal_wiki_management


class MockWiki:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "wiki_demo")
        self.owner_user_id = kwargs.get("owner_user_id", 7)
        self.owner_group_id = kwargs.get("owner_group_id", 8)
        self.owner_agent_id = kwargs.get("owner_agent_id", 11)
        self.mode = kwargs.get("mode", 0o640)
        self.title = kwargs.get("title", "Demo")
        self.description = kwargs.get("description", "Notes")
        self.root_node_id = kwargs.get("root_node_id", "wn_root")
        self.metadata = kwargs.get("metadata", {"kind": "tutor"})
        self.created_at = kwargs.get("created_at", MagicMock())
        self.updated_at = kwargs.get("updated_at", MagicMock())
        self.created_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"
        self.updated_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"

    @property
    def wiki_id(self) -> str:
        return str(self.id)


class MockNode:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "wn_leaf")
        self.wiki_id = kwargs.get("wiki_id", "wiki_demo")
        self.parent_id = kwargs.get("parent_id", "wn_root")
        self.node_type = kwargs.get("node_type", "leaf")
        self.title = kwargs.get("title", "Summary")
        self.body = kwargs.get("body", "Body")
        self.sort_order = kwargs.get("sort_order", 0)
        self.created_at = kwargs.get("created_at", MagicMock())
        self.updated_at = kwargs.get("updated_at", MagicMock())
        self.created_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"
        self.updated_at.isoformat.return_value = "2026-06-23T00:00:00+00:00"

    @property
    def node_id(self) -> str:
        return str(self.id)


def test_list_wikis_serializes_manager_results():
    mock_manager = MagicMock()
    mock_manager.list_wikis.return_value = [MockWiki()]

    with patch("src.api.internal.wiki_management.get_wiki_manager", return_value=mock_manager):
        result = internal_wiki_management.list_wikis(requester_user_id=7, requester_group_ids=set())

    assert result[0]["id"] == "wiki_demo"
    assert result[0]["owner_agent_id"] == 11
    assert result[0]["root_node_id"] == "wn_root"


def test_create_leaf_serializes_node():
    mock_manager = MagicMock()
    mock_manager.create_leaf.return_value = MockNode(id="wn_note", title="Takeaway")

    with patch("src.api.internal.wiki_management.get_wiki_manager", return_value=mock_manager):
        result = internal_wiki_management.create_leaf("wiki_demo", "wn_root", "Takeaway", body="Body")

    assert result["id"] == "wn_note"
    assert result["title"] == "Takeaway"
    assert result["body"] == "Body"
