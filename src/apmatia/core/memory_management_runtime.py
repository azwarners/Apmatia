from __future__ import annotations

from typing import TYPE_CHECKING

from apmatia.lib.memory_management.module import MemoryManager
from apmatia.core.runtime_paths import get_app_dir, get_data_dir

if TYPE_CHECKING:
    from apmatia.lib.memory_management.sqlite_repositories import SQLiteMemoryManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
MEMORY_DB_PATH = DATA_DIR / "memories.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_MEMORY_DB_PATH = MEMORY_DB_PATH


_bundle: "SQLiteMemoryManagementBundle | None" = None
_memory_manager: "MemoryManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _memory_manager

    if _bundle is None:
        from apmatia.lib.memory_management.sqlite_repositories import SQLiteMemoryManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = MEMORY_DB_PATH if MEMORY_DB_PATH != _DEFAULT_MEMORY_DB_PATH else data_dir / "memories.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteMemoryManagementBundle(db_path)
        _memory_manager = MemoryManager(_bundle.memories)


def get_memory_manager() -> MemoryManager:
    _ensure_runtime()
    assert _memory_manager is not None
    return _memory_manager
