from apmatia.lib.memory_management.models import MemoryItem


def test_memory_item_defaults():
    memory = MemoryItem(title="Note", content="Remember this")

    assert memory.id is None
    assert memory.title == "Note"
    assert memory.content == "Remember this"
    assert memory.tags == []
    assert memory.owner_agent_id is None
    assert memory.visibility == "draft"
    assert memory.status == "active"
    assert memory.source_message_ids == []
    assert memory.created_at.tzinfo is not None
    assert memory.updated_at.tzinfo is not None


def test_memory_item_normalizes_lists():
    memory = MemoryItem(
        title="Note",
        content="Remember this",
        tags=[" alpha ", "", "beta"],
        source_message_ids=[" 1 ", "", "2"],
    )

    assert memory.tags == ["alpha", "beta"]
    assert memory.source_message_ids == ["1", "2"]
