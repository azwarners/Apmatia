"""Generic portable-view renderer shared by Flet clients."""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from .errors import UnsupportedComponentError


class ViewRenderer:
    """Render portable view documents as Flet controls."""

    def __init__(self, on_intent: Callable[[dict[str, Any]], None]):
        self._on_intent = on_intent
        self._component_handlers = {
            "page": self._render_page,
            "panel": self._render_panel,
            "card": self._render_card,
            "form": self._render_form,
            "text": self._render_text,
            "field": self._render_field,
            "actions": self._render_actions,
            "notice": self._render_notice,
        }

    def render(self, component: dict[str, Any]) -> ft.Control:
        component_type = component.get("component_type", component.get("type"))
        handler = self._component_handlers.get(component_type)
        if handler is None:
            raise UnsupportedComponentError(f"Unsupported component type: {component_type}")
        return handler(component)

    def _render_page(self, component: dict[str, Any]) -> ft.Control:
        return ft.Container(
            content=ft.Column(controls=[self.render(child) for child in component.get("children", [])], expand=True),
            expand=True,
        )

    def _render_panel(self, component: dict[str, Any]) -> ft.Control:
        controls: list[ft.Control] = []
        properties = component.get("properties", component)
        title = properties.get("title")
        if title:
            controls.append(ft.Text(title, size=20, weight=ft.FontWeight.BOLD))
        controls.extend(self.render(child) for child in component.get("children", []))
        return ft.Container(content=ft.Column(controls=controls, spacing=16), padding=ft.Padding(24, 24, 24, 24))

    def _render_card(self, component: dict[str, Any]) -> ft.Control:
        return ft.Card(
            content=ft.Container(
                content=ft.Column(controls=[self.render(child) for child in component.get("children", [])], spacing=16),
                padding=ft.Padding(24, 24, 24, 24),
            )
        )

    def _render_form(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", {})
        fields: dict[str, ft.Control] = {}
        controls: list[ft.Control] = []
        actions = properties.get("actions") or []
        if not actions and properties.get("submit_label"):
            actions = [{"label": properties["submit_label"], "payload": {}}]
        title = properties.get("title")
        description = properties.get("description")
        if title:
            controls.append(ft.Text(title, size=20, weight=ft.FontWeight.BOLD))
        if description:
            controls.append(ft.Text(description))
        for child in component.get("children", []):
            field = self.render(child)
            key = (child.get("properties") or {}).get("key")
            if key:
                fields[key] = field
            controls.append(field)

        def submit(action: dict[str, Any]) -> None:
            values = {key: getattr(field, "value", "") or "" for key, field in fields.items()}
            payload = dict(action.get("payload") or {})
            payload.update(values)
            self._on_intent(payload)

        for field in fields.values():
            if actions and isinstance(field, ft.TextField):
                field.on_submit = lambda _event, action=actions[0]: submit(action)
        for action in actions:
            def on_click(_event: ft.ControlEvent, action: dict[str, Any] = action) -> None:
                submit(action)

            controls.append(ft.Button(action.get("label", "Submit"), on_click=on_click))
        return ft.Container(content=ft.Column(controls=controls, spacing=16), padding=ft.Padding(24, 24, 24, 24))

    def _render_text(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", {})
        return ft.Text(properties.get("content", component.get("content", "")))

    def _render_field(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", component)
        field_type = properties.get("field_type", properties.get("type", "text"))
        key = properties.get("key", "")
        label = properties.get("label", key)
        if field_type == "password":
            return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}", password=True, can_reveal_password=True)
        if field_type == "textarea":
            return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}", multiline=True, min_lines=4)
        return ft.TextField(key=key, label=label, hint_text=f"Enter {label.lower()}")

    def _render_actions(self, component: dict[str, Any]) -> ft.Control:
        def on_click(event: ft.ControlEvent) -> None:
            del event
            self._on_intent(component.get("payload", {}))

        properties = component.get("properties", component)
        label = properties.get("label", "Action")
        return ft.Button(label, on_click=on_click)

    def _render_notice(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", component)
        return ft.Container(content=ft.Text(properties.get("message", "")), padding=ft.Padding(12, 12, 12, 12))
