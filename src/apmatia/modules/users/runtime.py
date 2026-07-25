from __future__ import annotations

from typing import TYPE_CHECKING

from .auth import SessionManager
from apmatia.core.runtime_paths import get_app_dir, get_data_dir
from .manager import GroupManager, UserManager

if TYPE_CHECKING:
    from .sqlite_repositories import SQLiteUserManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
USER_DB_PATH = DATA_DIR / "users.db"
SESSION_DB_PATH = DATA_DIR / "auth_sessions.json"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_USER_DB_PATH = USER_DB_PATH
_DEFAULT_SESSION_DB_PATH = SESSION_DB_PATH


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
        from .sqlite_repositories import SQLiteUserManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        user_db_path = USER_DB_PATH if USER_DB_PATH != _DEFAULT_USER_DB_PATH else data_dir / "users.db"
        session_db_path = (
            SESSION_DB_PATH if SESSION_DB_PATH != _DEFAULT_SESSION_DB_PATH else data_dir / "auth_sessions.json"
        )
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteUserManagementBundle(user_db_path)
        _user_manager = UserManager(_bundle.users)
        _group_manager = GroupManager(_bundle.groups, _bundle.memberships)
        _session_manager = SessionManager(session_db_path)


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
