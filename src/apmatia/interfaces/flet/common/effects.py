"""Client-side effect execution shared by Flet clients."""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from .errors import UnsupportedEffectError
from .state import ClientState


class EffectExecutor:
    """Execute portable view-contract effects."""

    def __init__(self, page: ft.Page, state: ClientState):
        self._page = page
        self._state = state
        self._effects: dict[str, Callable] = {
            "set_state": self._set_state,
            "clear_state": self._clear_state,
            "navigate": self._navigate,
            "show_notification": self._show_notification,
            "refresh_view": self._refresh_view,
        }

    def execute(self, effect_type: str, payload: dict[str, Any]) -> None:
        handler = self._effects.get(effect_type)
        if handler is None:
            raise UnsupportedEffectError(f"Unsupported effect: {effect_type}")
        handler(payload)

    def _set_state(self, payload: dict[str, Any]) -> None:
        key = payload.get("key")
        value = payload.get("value")
        scope = payload.get("scope", "view")
        if scope == "event":
            self._state.set_event(key, value)
        elif scope == "view":
            self._state.set_view(key, value)
        elif scope == "session":
            self._state.set_session(key, value)

    def _clear_state(self, payload: dict[str, Any]) -> None:
        scope = payload.get("scope", "view")
        if scope == "event":
            self._state.clear_event()
        elif scope == "view":
            self._state.clear_view()
        elif scope == "session":
            self._state.clear_session()

    def _navigate(self, payload: dict[str, Any]) -> None:
        route = payload.get("route")
        if route:
            self._page.route = route

    def _show_notification(self, payload: dict[str, Any]) -> None:
        self._page.snack_bar(payload.get("message", ""), duration=3000).show()

    def _refresh_view(self, payload: dict[str, Any]) -> None:
        del payload
        self._page.update()
