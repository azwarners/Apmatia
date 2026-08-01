"""Form components shared by Flet clients."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft


def render_form(form_spec: dict[str, Any], on_submit: Callable[[dict[str, str]], None]) -> ft.Container:
    """Render a portable form as a Flet container."""
    fields: list[ft.Control] = []
    field_map: dict[str, ft.TextField] = {}
    for field_spec in form_spec.get("fields", []):
        key = field_spec["key"]
        label = field_spec.get("label", key)
        text_field = ft.TextField(
            label=label,
            hint_text=f"Enter {label.lower()}",
            password=field_spec.get("type") == "password",
            can_reveal_password=field_spec.get("type") == "password",
        )
        field_map[key] = text_field
        fields.append(text_field)

    def on_click(event: ft.ControlEvent) -> None:
        del event
        on_submit({key: field.value or "" for key, field in field_map.items()})

    fields.append(ft.Button(form_spec.get("submit_label", "Submit"), on_click=on_click))
    return ft.Container(content=ft.Column(controls=fields, spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=ft.Padding(24, 24, 24, 24))
