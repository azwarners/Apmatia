from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.app_config import get_config_value
from apmatia.core.ipe_runtime import get_ipe_service
from apmatia.core.runtime_paths import get_app_dir, get_data_dir
from apmatia.core.memory_management_runtime import get_memory_manager
from apmatia.core.wiki_management_runtime import get_wiki_manager
from apmatia.modules.apmatia_admin.tooling import (
    apmatia_admin_tool_definitions,
    build_apmatia_admin_tool_providers,
)
from apmatia.modules.ipe.tools import build_ipe_tool_providers, ipe_tool_definitions
from apmatia.modules.agent_loops.tools import build_agent_loop_tool_providers, agent_loop_tool_definitions
from apmatia.modules.agent_config.tooling import build_agent_config_tool_providers, agent_config_tool_definitions
from apmatia.modules.os_admin.tooling import build_os_admin_tool_providers, os_admin_tool_definitions
from apmatia.modules.os_admin.tooling import OS_ADMIN_PROVIDER_ID
from apmatia.modules.memory_manager.tooling import build_memory_tool_providers, memory_tool_definitions
from apmatia.modules.dev_tools.tooling import build_dev_tools_tool_providers, dev_tools_tool_definitions
from apmatia.lib.tool_management.module import ToolManager
from apmatia.lib.tool_management.workspace_modules import (
    build_workspace_module_tool_providers,
    workspace_module_tool_definitions,
)
from apmatia.lib.tool_management.workspace_files import (
    build_workspace_file_tool_providers,
    workspace_file_tool_definitions,
)
from apmatia.modules.knowledge_wiki.tooling import build_wiki_tool_providers, wiki_tool_definitions

if TYPE_CHECKING:
    from apmatia.lib.tool_management.repositories import ToolDefinitionRepository
    from apmatia.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
TOOL_DB_PATH = DATA_DIR / "tools.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_TOOL_DB_PATH = TOOL_DB_PATH


_bundle: "SQLiteToolManagementBundle | None" = None
_tool_manager: "ToolManager | None" = None
_tool_manager_development_mode: bool | None = None


def _ensure_runtime() -> None:
    global _bundle
    global _tool_manager
    global _tool_manager_development_mode

    development_enabled = bool(get_config_value("ui", "show_development_modules", default=False))
    if _bundle is None or _tool_manager_development_mode != development_enabled:
        from apmatia.lib.tool_management.sqlite_repositories import SQLiteToolManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = TOOL_DB_PATH if TOOL_DB_PATH != _DEFAULT_TOOL_DB_PATH else data_dir / "tools.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteToolManagementBundle(db_path)
        _set_apmatia_admin_tool_definitions_enabled(_bundle.tools, development_enabled=development_enabled)
        _set_dev_tools_tool_definitions_enabled(_bundle.tools, development_enabled=development_enabled)
        _migrate_os_admin_tool_definition(_bundle.tools, development_enabled=development_enabled)
        _set_memory_tool_definitions_enabled(_bundle.tools, development_enabled=development_enabled)
        _set_knowledge_wiki_tool_definitions_enabled(_bundle.tools, development_enabled=development_enabled)
        agent_manager = get_agent_manager()
        _tool_manager = ToolManager(
            _bundle.tools,
            _bundle.assignments,
            agent_manager,
            builtin_providers=[
                *(build_apmatia_admin_tool_providers(agent_manager) if development_enabled else []),
                *build_ipe_tool_providers(get_ipe_service(), agent_manager),
                *(build_os_admin_tool_providers(agent_manager) if development_enabled else []),
                *(build_memory_tool_providers(get_memory_manager(), agent_manager) if development_enabled else []),
                *build_agent_config_tool_providers(get_app_dir()),
                *(build_dev_tools_tool_providers(agent_manager) if development_enabled else []),
                *(build_wiki_tool_providers(get_wiki_manager(), agent_manager) if development_enabled else []),
                *build_workspace_file_tool_providers(agent_manager),
                *build_workspace_module_tool_providers(),
                *build_agent_loop_tool_providers(agent_manager),
            ],
            builtin_definitions=[
                *(apmatia_admin_tool_definitions() if development_enabled else []),
                *ipe_tool_definitions(),
                *agent_loop_tool_definitions(),
                *(os_admin_tool_definitions() if development_enabled else []),
                *(memory_tool_definitions() if development_enabled else []),
                *agent_config_tool_definitions(),
                *(dev_tools_tool_definitions() if development_enabled else []),
                *(wiki_tool_definitions() if development_enabled else []),
                *workspace_file_tool_definitions(),
                *workspace_module_tool_definitions(),
            ],
        )
        _tool_manager_development_mode = development_enabled


def _migrate_os_admin_tool_definition(
    tool_repo: "ToolDefinitionRepository",
    *,
    development_enabled: bool,
) -> None:
    legacy = tool_repo.get_by_provider_id("builtin.apmatia_system_audit")
    current = tool_repo.get_by_provider_id(OS_ADMIN_PROVIDER_ID)
    target = legacy or current
    if target is None:
        return

    payload = os_admin_tool_definitions()[0]
    tool_repo.update(
        replace(
            target,
            name=payload["name"],
            description=payload["description"],
            input_schema=payload["input_schema"],
            output_schema=payload["output_schema"],
            provider_id=payload["provider_id"],
            enabled=development_enabled,
            confirmation_required=payload["confirmation_required"],
            read_only=payload["read_only"],
            metadata=payload["metadata"],
        )
    )
    if legacy is not None and current is not None and legacy.id != current.id and current.id is not None:
        tool_repo.delete(current.id)


def _set_apmatia_admin_tool_definitions_enabled(
    tool_repo: "ToolDefinitionRepository",
    *,
    development_enabled: bool,
) -> None:
    for payload in apmatia_admin_tool_definitions():
        existing = tool_repo.get_by_provider_id(str(payload["provider_id"]))
        if existing is None or existing.enabled == development_enabled:
            continue
        tool_repo.update(
            replace(
                existing,
                enabled=development_enabled,
                metadata=payload["metadata"],
            )
        )


def _set_dev_tools_tool_definitions_enabled(
    tool_repo: "ToolDefinitionRepository",
    *,
    development_enabled: bool,
) -> None:
    for payload in dev_tools_tool_definitions():
        existing = tool_repo.get_by_provider_id(str(payload["provider_id"]))
        if existing is None or existing.enabled == development_enabled:
            continue
        tool_repo.update(replace(existing, enabled=development_enabled))


def _set_memory_tool_definitions_enabled(
    tool_repo: "ToolDefinitionRepository",
    *,
    development_enabled: bool,
) -> None:
    for payload in memory_tool_definitions():
        existing = tool_repo.get_by_provider_id(str(payload["provider_id"]))
        if existing is None or existing.enabled == development_enabled:
            continue
        tool_repo.update(replace(existing, enabled=development_enabled))


def _set_knowledge_wiki_tool_definitions_enabled(
    tool_repo: "ToolDefinitionRepository",
    *,
    development_enabled: bool,
) -> None:
    for payload in wiki_tool_definitions():
        existing = tool_repo.get_by_provider_id(str(payload["provider_id"]))
        if existing is None or existing.enabled == development_enabled:
            continue
        tool_repo.update(replace(existing, enabled=development_enabled))


def get_tool_manager() -> ToolManager:
    _ensure_runtime()
    assert _tool_manager is not None
    return _tool_manager
