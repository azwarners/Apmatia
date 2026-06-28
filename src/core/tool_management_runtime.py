from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.agent_management_runtime import get_agent_manager
from src.core.memory_management_runtime import get_memory_manager
from src.lib.system_audit.tooling import (
    build_system_audit_tool_providers,
    system_audit_tool_definitions,
)
from src.core.wiki_management_runtime import get_wiki_manager
from src.lib.apmatia_administration.tooling import (
    apmatia_administration_tool_definitions,
    build_apmatia_administration_tool_providers,
)
from src.lib.memory_management.tooling import build_memory_tool_providers, memory_tool_definitions
from src.lib.tool_management.module import ToolManager
from src.lib.wiki_management.tooling import build_wiki_tool_providers, wiki_tool_definitions

if TYPE_CHECKING:
    from src.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
TOOL_DB_PATH = DATA_DIR / "tools.db"


_bundle: "SQLiteToolManagementBundle | None" = None
_tool_manager: "ToolManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _tool_manager

    if _bundle is None:
        from src.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteToolManagementBundle(TOOL_DB_PATH)
        agent_manager = get_agent_manager()
        _tool_manager = ToolManager(
            _bundle.tools,
            _bundle.assignments,
            agent_manager,
            builtin_providers=[
                *build_apmatia_administration_tool_providers(agent_manager),
                *build_system_audit_tool_providers(agent_manager),
                *build_memory_tool_providers(get_memory_manager(), agent_manager),
                *build_wiki_tool_providers(get_wiki_manager(), agent_manager),
            ],
            builtin_definitions=[
                *apmatia_administration_tool_definitions(),
                *system_audit_tool_definitions(),
                *memory_tool_definitions(),
                *wiki_tool_definitions(),
            ],
        )


def get_tool_manager() -> ToolManager:
    _ensure_runtime()
    assert _tool_manager is not None
    return _tool_manager
