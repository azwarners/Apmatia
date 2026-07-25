from __future__ import annotations

from dataclasses import replace

import pytest

from apmatia.modules.memory_manager.models import MemoryItem
from apmatia.modules.memory_manager.manager import MemoryManager
from apmatia.modules.memory_manager.repositories import MemoryRepository


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self._memories: dict[int, MemoryItem] = {}
        self._next_id = 1

    def create(self, memory: MemoryItem) -> int:
        memory_id = self._next_id
        self._next_id += 1
        self._memories[memory_id] = replace(memory, id=memory_id)
        return memory_id

    def get(self, memory_id: int) -> MemoryItem | None:
        return self._memories.get(memory_id)

    def list_all(self) -> list[MemoryItem]:
        return list(self._memories.values())

    def search(self, query: str, **kwargs) -> list[MemoryItem]:
        text = query.lower().strip()
        memories = list(self._memories.values())
        if not text:
            return memories
        return [
            memory
            for memory in memories
            if text in memory.title.lower()
            or text in memory.content.lower()
            or any(text in tag.lower() for tag in memory.tags)
        ]

    def update(self, memory: MemoryItem) -> None:
        self._memories[int(memory.id)] = memory


@pytest.fixture
def memory_manager() -> MemoryManager:
    return MemoryManager(InMemoryMemoryRepository())


def test_memory_manager_crud(memory_manager: MemoryManager):
    created = memory_manager.create_memory(
        "Trip note",
        "Bring passport",
        owner_user_id=7,
        owner_agent_id=11,
        tags=["travel"],
        visibility="user_visible",
    )

    fetched = memory_manager.get_memory(created.id, requester_user_id=7, requester_group_ids=set())

    assert fetched is not None
    assert fetched.title == "Trip note"
    assert fetched.tags == ["travel"]
    assert fetched.owner_agent_id == 11
    assert fetched.visibility == "user_visible"

    updated = memory_manager.update_memory(
        int(created.id),
        requester_user_id=7,
        requester_group_ids=set(),
        content="Bring passport and charger",
        tags=["travel", "packing"],
    )

    assert updated.content == "Bring passport and charger"
    assert updated.tags == ["travel", "packing"]


def test_memory_manager_can_filter_by_owner_agent(memory_manager: MemoryManager):
    memory_manager.create_memory("Alpha", "One", owner_user_id=7, owner_agent_id=10, visibility="user_visible")
    memory_manager.create_memory("Beta", "Two", owner_user_id=7, owner_agent_id=11, visibility="user_visible")

    results = memory_manager.list_memories(
        requester_user_id=7,
        requester_group_ids=set(),
        owner_agent_id=11,
    )

    assert [memory.title for memory in results] == ["Beta"]


def test_memory_manager_search_filters_to_requester(memory_manager: MemoryManager):
    memory_manager.create_memory("Alpha", "One", owner_user_id=7, visibility="user_visible", tags=["ops"])
    memory_manager.create_memory("Beta", "Two", owner_user_id=8, visibility="user_visible", tags=["ops"])

    results = memory_manager.search_memories(
        "ops",
        requester_user_id=7,
        requester_group_ids=set(),
        owner_user_id=7,
    )

    assert [memory.title for memory in results] == ["Alpha"]


def test_memory_manager_archive_and_delete(memory_manager: MemoryManager):
    created = memory_manager.create_memory("Alpha", "One", owner_user_id=7)

    archived = memory_manager.archive_memory(int(created.id), requester_user_id=7, requester_group_ids=set())
    assert archived.status == "archived"

    active_results = memory_manager.list_memories(requester_user_id=7, requester_group_ids=set())
    assert active_results == []

    deleted = memory_manager.delete_memory(int(created.id), requester_user_id=7, requester_group_ids=set())
    assert deleted.status == "deleted"

    assert memory_manager.get_memory(int(created.id), requester_user_id=7, requester_group_ids=set()) is None


def test_memory_manager_blocks_other_users_from_private_items(memory_manager: MemoryManager):
    created = memory_manager.create_memory("Alpha", "One", owner_user_id=7, visibility="private")

    assert memory_manager.get_memory(int(created.id), requester_user_id=8, requester_group_ids=set()) is None

    with pytest.raises(PermissionError):
        memory_manager.update_memory(
            int(created.id),
            requester_user_id=8,
            requester_group_ids=set(),
            title="Nope",
        )
