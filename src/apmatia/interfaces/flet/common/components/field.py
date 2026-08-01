"""Field components shared by Flet clients."""

from __future__ import annotations

from typing import Any

import flet as ft


def render_field(field_spec: dict[str, Any]) -> ft.Control:
    """Render a portable field as a Flet control."""
    field_type = field_spec.get("type", "text")
    key = field_spec["key"]
    label = field_spec.get("label", key)
    required = field_spec.get("required", False)
    if field_type == "password":
        return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}", password=True, can_reveal_password=True)
    if field_type == "textarea":
        return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}", multiline=True, min_lines=4)
    if field_type == "number":
        return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}", keyboard_type=ft.KeyboardType.NUMBER)
    if field_type == "checkbox":
        return ft.Checkbox(key=key, label=label)
    if field_type == "select":
        options = field_spec.get("options", [])
        return ft.Dropdown(key=key, label=label, options=[ft.dropdown.Option(opt["value"], opt["label"]) for opt in options])
    return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}")
