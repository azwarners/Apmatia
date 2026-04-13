from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.lib.user_management.auth import SessionManager
from src.lib.user_management.module import GroupManager, UserManager

if TYPE_CHECKING:
    from src.lib.user_management.sqlite_repositories import SQLiteUserManagementBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
USER_DB_PATH = DATA_DIR / "users.db"


_bundle: "SQLiteUserManagementBundle | None" = None
_user_manager: UserManager | None = None
_group_manager: GroupManager | None = None
_session_manager: SessionManager | None = None


def _ensure_runtime() -> None:
    global _bundle
    global _user_manager
    global _group_manager
    global _session_manager

    if _bundle is None:
        from src.lib.user_management.sqlite_repositories import SQLiteUserManagementBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteUserManagementBundle(USER_DB_PATH)
        _user_manager = UserManager(_bundle.users)
        _group_manager = GroupManager(_bundle.groups, _bundle.memberships)
        _session_manager = SessionManager()


def get_user_manager() -> UserManager:
    _ensure_runtime()
    assert _user_manager is not None
    return _user_manager


def get_group_manager() -> GroupManager:
    _ensure_runtime()
    assert _group_manager is not None
    return _group_manager


def get_session_manager() -> SessionManager:
    _ensure_runtime()
    assert _session_manager is not None
    return _session_manager
