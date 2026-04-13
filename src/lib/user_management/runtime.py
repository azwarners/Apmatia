from __future__ import annotations

# Backward-compatible import path; Apmatia-specific runtime wiring now lives in
# src.core.user_management_runtime so src.lib.user_management remains reusable.
from src.core.user_management_runtime import (  # noqa: F401
    APP_DIR,
    DATA_DIR,
    USER_DB_PATH,
    get_group_manager,
    get_session_manager,
    get_user_manager,
)

__all__ = [
    "APP_DIR",
    "DATA_DIR",
    "USER_DB_PATH",
    "get_user_manager",
    "get_group_manager",
    "get_session_manager",
]
