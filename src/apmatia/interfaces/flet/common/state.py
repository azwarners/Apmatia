"""Client view/session state abstraction shared by Flet clients."""

from __future__ import annotations

from typing import Any

import flet as ft


class ClientState:
    """Abstraction for event, view, and client-session state."""

    def __init__(self, page: ft.Page):
        self._page = page
        self._event_state: dict[str, Any] = {}
        self._view_state: dict[str, Any] = {}
        self._session_state: dict[str, Any] = {}

    def set_event(self, key: str, value: Any) -> None:
        self._event_state[key] = value

    def get_event(self, key: str, default: Any = None) -> Any:
        return self._event_state.get(key, default)

    def clear_event(self) -> None:
        self._event_state.clear()

    def set_view(self, key: str, value: Any) -> None:
        self._view_state[key] = value

    def get_view(self, key: str, default: Any = None) -> Any:
        return self._view_state.get(key, default)

    def clear_view(self) -> None:
        self._view_state.clear()

    def set_session(self, key: str, value: Any) -> None:
        self._session_state[key] = value

    def get_session(self, key: str, default: Any = None) -> Any:
        return self._session_state.get(key, default)

    def clear_session(self) -> None:
        self._session_state.clear()

    @property
    def is_authenticated(self) -> bool:
        return bool(self._session_state.get("authenticated", False))

    def set_authenticated(self, user_info: dict[str, Any]) -> None:
        self._session_state["authenticated"] = True
        self._session_state["user_id"] = user_info.get("user_id")
        self._session_state["username"] = user_info.get("username")

    def clear_authentication(self) -> None:
        self._session_state["authenticated"] = False
        self._session_state.pop("user_id", None)
        self._session_state.pop("username", None)

    @property
    def username(self) -> str | None:
        return self._session_state.get("username")
