from __future__ import annotations

from typing import TYPE_CHECKING

from apmatia.core.runtime_paths import get_app_dir, get_data_dir
from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.apmatia_ipe_runtime import get_ipe_service
from apmatia.core.memory_management_runtime import get_memory_manager
from apmatia.core.wiki_management_runtime import get_wiki_manager
from apmatia.lib.apmatia_administration.tooling import (
    apmatia_administration_tool_definitions,
    build_apmatia_administration_tool_providers,
)
from apmatia.modules.apmatia_ipe.tools import build_ipe_tool_providers, ipe_tool_definitions
from apmatia.lib.system_audit.tooling import build_system_audit_tool_providers, system_audit_tool_definitions
from apmatia.lib.memory_management.tooling import build_memory_tool_providers, memory_tool_definitions
from apmatia.lib.tool_management.module import ToolManager
from apmatia.lib.tool_management.workspace_modules import (
    build_workspace_module_tool_providers,
    workspace_module_tool_definitions,
)
from apmatia.lib.wiki_management.tooling import build_wiki_tool_providers, wiki_tool_definitions
from apmatia.core.runtime_paths import get_app_dir, get_data_dir

if TYPE_CHECKING:
    from apmatia.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
TOOL_DB_PATH = DATA_DIR / "tools.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_TOOL_DB_PATH = TOOL_DB_PATH


_bundle: "SQLiteToolManagementBundle | None" = None
_tool_manager: "ToolManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _tool_manager

    if _bundle is None:
        from apmatia.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = TOOL_DB_PATH if TOOL_DB_PATH != _DEFAULT_TOOL_DB_PATH else data_dir / "tools.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteToolManagementBundle(db_path)
        agent_manager = get_agent_manager()
        _tool_manager = ToolManager(
            _bundle.tools,
            _bundle.assignments,
            agent_manager,
            builtin_providers=[
                *build_apmatia_administration_tool_providers(agent_manager),
                *build_ipe_tool_providers(get_ipe_service(), agent_manager),
                *build_system_audit_tool_providers(agent_manager),
                *build_memory_tool_providers(get_memory_manager(), agent_manager),
                *build_wiki_tool_providers(get_wiki_manager(), agent_manager),
                *build_workspace_module_tool_providers(),
            ],
            builtin_definitions=[
                *apmatia_administration_tool_definitions(),
                *ipe_tool_definitions(),
                *system_audit_tool_definitions(),
                *memory_tool_definitions(),
                *wiki_tool_definitions(),
                *workspace_module_tool_definitions(),
            ],
        )


def get_tool_manager() -> ToolManager:
    _ensure_runtime()
    assert _tool_manager is not None
    return _tool_manager
