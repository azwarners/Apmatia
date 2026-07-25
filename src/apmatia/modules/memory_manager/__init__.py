"""Memory manager module for persisted agent memories."""

from .models import MEMORY_STATUSES, MEMORY_VISIBILITIES, MemoryItem
from .manager import MemoryManager
from .repositories import MemoryRepository
from .services import MemoryService
from .tooling import build_memory_tool_providers, memory_tool_definitions

try:
    from .sqlite_repositories import (
        MemoryManagementTables,
        SQLiteMemoryManagementBundle,
        SQLiteMemoryRepository,
    )
except ModuleNotFoundError:
    MemoryManagementTables = None
    SQLiteMemoryManagementBundle = None
    SQLiteMemoryRepository = None

__all__ = [
    "MEMORY_STATUSES",
    "MEMORY_VISIBILITIES",
    "MemoryItem",
    "MemoryManager",
    "MemoryRepository",
    "MemoryService",
    "build_memory_tool_providers",
    "memory_tool_definitions",
]

if SQLiteMemoryRepository is not None:
    __all__.extend(
        [
            "MemoryManagementTables",
            "SQLiteMemoryManagementBundle",
            "SQLiteMemoryRepository",
        ]
    )
