"""Unit tests for SQLite-backed memory repositories."""

import tempfile

import pytest

from src.lib.memory_management.models import MemoryItem
from src.lib.memory_management.sqlite_repositories import (
    MemoryManagementTables,
    SQLiteMemoryManagementBundle,
    SQLiteMemoryRepository,
)


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        yield handle.name


@pytest.fixture
def memory_repo(temp_db_path):
    try:
        from persistence import SQLiteStore
    except ModuleNotFoundError:
        from src.lib.persistence.persistence import SQLiteStore
    store = SQLiteStore(temp_db_path)
    return SQLiteMemoryRepository(store, MemoryManagementTables())


def test_sqlite_memory_repository_round_trip(memory_repo: SQLiteMemoryRepository):
    memory_id = memory_repo.create(
        MemoryItem(
            title="Trip note",
            content="Bring passport",
            owner_user_id=7,
            owner_agent_id=12,
            tags=["travel"],
            source_discussion_id="disc-1",
        )
    )

    retrieved = memory_repo.get(memory_id)

    assert retrieved is not None
    assert retrieved.title == "Trip note"
    assert retrieved.tags == ["travel"]
    assert retrieved.owner_agent_id == 12
    assert retrieved.source_discussion_id == "disc-1"


def test_sqlite_memory_repository_search(memory_repo: SQLiteMemoryRepository):
    memory_repo.create(MemoryItem(title="Packing", content="Bring charger", owner_user_id=7, tags=["travel"]))
    memory_repo.create(MemoryItem(title="Groceries", content="Buy apples", owner_user_id=7, tags=["home"]))

    results = memory_repo.search("charger")

    assert len(results) == 1
    assert results[0].title == "Packing"


def test_sqlite_memory_management_bundle_persists(temp_db_path):
    bundle_a = SQLiteMemoryManagementBundle(temp_db_path)
    memory_id = bundle_a.memories.create(MemoryItem(title="Alpha", content="One", owner_user_id=7))

    bundle_b = SQLiteMemoryManagementBundle(temp_db_path)
    retrieved = bundle_b.memories.get(memory_id)

    assert retrieved is not None
    assert retrieved.title == "Alpha"
