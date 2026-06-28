from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.lib.agent_management.module import AgentManager

if TYPE_CHECKING:
    from src.lib.agent_management.sqlite_repositories import SQLiteAgentManagementBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
AGENT_DB_PATH = DATA_DIR / "agents.db"


_bundle: "SQLiteAgentManagementBundle | None" = None
_agent_manager: "AgentManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _agent_manager

    if _bundle is None:
        from src.lib.agent_management.sqlite_repositories import SQLiteAgentManagementBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteAgentManagementBundle(AGENT_DB_PATH)
        _agent_manager = AgentManager(_bundle.agents, _bundle.prompts)


def get_agent_manager() -> AgentManager:
    _ensure_runtime()
    assert _agent_manager is not None
    return _agent_manager
