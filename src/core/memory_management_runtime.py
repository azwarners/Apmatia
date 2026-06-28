from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.lib.memory_management.module import MemoryManager

if TYPE_CHECKING:
    from src.lib.memory_management.sqlite_repositories import SQLiteMemoryManagementBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
MEMORY_DB_PATH = DATA_DIR / "memories.db"


_bundle: "SQLiteMemoryManagementBundle | None" = None
_memory_manager: "MemoryManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _memory_manager

    if _bundle is None:
        from src.lib.memory_management.sqlite_repositories import SQLiteMemoryManagementBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteMemoryManagementBundle(MEMORY_DB_PATH)
        _memory_manager = MemoryManager(_bundle.memories)


def get_memory_manager() -> MemoryManager:
    _ensure_runtime()
    assert _memory_manager is not None
    return _memory_manager
