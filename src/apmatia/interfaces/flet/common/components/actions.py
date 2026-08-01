"""Action components shared by Flet clients."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft


def render_action(action_spec: dict[str, Any], on_click: Callable[[], None]) -> ft.Control:
    """Render a portable action as a Flet button."""
    return ft.Button(action_spec.get("label", "Action"), on_click=on_click)
