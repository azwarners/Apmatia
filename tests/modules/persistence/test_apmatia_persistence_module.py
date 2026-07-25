from __future__ import annotations

import json
from pathlib import Path

from apmatia.core.registry import Registry
from apmatia.modules.persistence import (
    PersistenceDescriptor,
    PersistenceRegistry,
    SQLiteStore,
    load_config_file,
    save_config_file,
)
from apmatia.modules.persistence.module import APMATIA_PERSISTENCE_MODULE, register


def test_persistence_module_is_stable_infrastructure() -> None:
    registry = Registry()

    register(registry)

    assert registry.list_modules() == [APMATIA_PERSISTENCE_MODULE]
    assert APMATIA_PERSISTENCE_MODULE.status.value == "stable"
    assert APMATIA_PERSISTENCE_MODULE.category.value == "infrastructure"


def test_sqlite_store_supports_document_lifecycle(tmp_path: Path) -> None:
    with SQLiteStore(tmp_path / "persistence.sqlite3") as store:
        record_id = store.insert("records", {"name": "alpha", "body": "A"})
        assert store.get("records", id=record_id) == {"name": "alpha", "body": "A", "id": record_id}

        assert store.update("records", {"id": record_id}, {"name": "beta"}) == 1
        store.append("records", record_id, "body", "B")
        assert store.get("records", name="beta") == {"name": "beta", "body": "AB", "id": record_id}

        assert store.delete("records", id=record_id) == 1
        assert store.find("records") == []


def test_config_file_round_trip_and_fallback(tmp_path: Path) -> None:
    config_path = tmp_path / "nested" / "config.json"
    payload = {"ui": {"theme": "dark"}, "enabled": True}

    save_config_file(config_path, payload)

    assert json.loads(config_path.read_text(encoding="utf-8")) == payload
    assert load_config_file(config_path) == payload
    assert load_config_file(tmp_path / "missing.json", {"fallback": True}) == {"fallback": True}


def test_persistence_registry_lists_descriptors_deterministically() -> None:
    registry = PersistenceRegistry()
    registry.register(PersistenceDescriptor("zeta", "Zeta"))
    registry.register(PersistenceDescriptor("alpha", "Alpha"))

    assert [descriptor.persistence_id for descriptor in registry.list()] == ["alpha", "zeta"]
