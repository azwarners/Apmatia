from __future__ import annotations

from typing import TYPE_CHECKING

from .manager import AgentManager
from apmatia.core.runtime_paths import get_app_dir, get_data_dir

if TYPE_CHECKING:
    from .sqlite_repositories import SQLiteAgentManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
AGENT_DB_PATH = DATA_DIR / "agents.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_AGENT_DB_PATH = AGENT_DB_PATH


_bundle: "SQLiteAgentManagementBundle | None" = None
_agent_manager: "AgentManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _agent_manager

    if _bundle is None:
        from .sqlite_repositories import SQLiteAgentManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = AGENT_DB_PATH if AGENT_DB_PATH != _DEFAULT_AGENT_DB_PATH else data_dir / "agents.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteAgentManagementBundle(db_path)
        _agent_manager = AgentManager(_bundle.agents, _bundle.prompts)


def get_agent_manager() -> AgentManager:
    _ensure_runtime()
    assert _agent_manager is not None
    return _agent_manager
