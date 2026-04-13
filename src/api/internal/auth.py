from __future__ import annotations

from src.core.user_management_runtime import get_session_manager, get_user_manager


def has_any_users() -> bool:
    return len(get_user_manager().list_users()) > 0


def register_user(username: str, password: str):
    return get_user_manager().create_user(username=username, password=password)


def login_user(username: str, password: str):
    manager = get_user_manager()
    if not manager.verify_user(username=username, password=password):
        return None

    user = next((u for u in manager.list_users() if u.username == username), None)
    if user is None or user.id is None:
        return None
    return get_session_manager().create_session(user_id=user.id, username=user.username)


def get_session(token: str | None):
    return get_session_manager().get_session(token)


def logout_session(token: str | None) -> bool:
    return get_session_manager().delete_session(token)

