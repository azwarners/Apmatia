from __future__ import annotations

from apmatia.modules.auth.runtime import (
    get_session,
    has_any_users,
    login_user,
    logout_session,
    register_user,
)
from apmatia.core.registry import get_application_registry
from apmatia.core.view_contract import normalize_view_document


def list_auth_views() -> list[dict]:
    return [
        normalize_view_document(view).to_dict()
        for view in get_application_registry().list_views()
        if view.module_id == "auth"
        and str((view.metadata.get("ui") or {}).get("navigation") or "")
        == "pre_authentication"
    ]

__all__ = [
    "get_session",
    "has_any_users",
    "login_user",
    "list_auth_views",
    "logout_session",
    "register_user",
]
