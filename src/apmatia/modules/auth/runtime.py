from __future__ import annotations

from apmatia.core.runtime_paths import get_data_dir
from apmatia.modules.users.runtime import get_user_manager

from .sessions import AuthSession, SessionManager

DATA_DIR = get_data_dir()
SESSION_DB_PATH = DATA_DIR / "auth_sessions.json"
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_SESSION_DB_PATH = SESSION_DB_PATH

_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _session_manager

    if _session_manager is None:
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        session_db_path = (
            SESSION_DB_PATH if SESSION_DB_PATH != _DEFAULT_SESSION_DB_PATH else data_dir / "auth_sessions.json"
        )
        data_dir.mkdir(parents=True, exist_ok=True)
        _session_manager = SessionManager(session_db_path)
    return _session_manager


def has_any_users() -> bool:
    return len(get_user_manager().list_users()) > 0


def register_user(username: str, password: str):
    return get_user_manager().create_user(username=username, password=password)


def login_user(username: str, password: str) -> AuthSession | None:
    manager = get_user_manager()
    if not manager.verify_user(username=username, password=password):
        return None

    user = next((item for item in manager.list_users() if item.username == username), None)
    if user is None or user.id is None:
        return None
    return get_session_manager().create_session(user_id=user.id, username=user.username)


def get_session(token: str | None) -> AuthSession | None:
    return get_session_manager().get_session(token)


def logout_session(token: str | None) -> bool:
    return get_session_manager().delete_session(token)
