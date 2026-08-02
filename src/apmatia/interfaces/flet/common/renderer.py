"""Generic portable-view renderer shared by Flet clients."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

import flet as ft

from .errors import UnsupportedComponentError


class ViewRenderer:
    """Render portable view documents as Flet controls."""

    def __init__(self, on_intent: Callable[[dict[str, Any]], None]):
        self._on_intent = on_intent
        self._actions: Mapping[str, dict[str, Any]] = {}
        self._data_sources: Mapping[str, Any] = {}
        self._state: Mapping[str, Any] = {}
        self._view_id = ""
        self._item_context: Mapping[str, Any] | None = None
        self._component_handlers = {
            "page": self._render_page,
            "panel": self._render_panel,
            "card": self._render_card,
            "form": self._render_form,
            "text": self._render_text,
            "field": self._render_field,
            "actions": self._render_actions,
            "notice": self._render_notice,
            "collection": self._render_collection,
            "table": self._render_collection,
            "columns": self._render_columns,
            "timeline": self._render_timeline,
            "message": self._render_message,
            "status": self._render_status,
            "navigation": self._render_navigation,
            "tabs": self._render_tabs,
            "terminal": self._render_terminal,
            "checklist": self._render_checklist,
            "progress": self._render_progress,
            "tree": self._render_tree,
            "markdown": self._render_markdown,
            "expander": self._render_expander,
        }

    def render(self, component: dict[str, Any], **context: Any) -> ft.Control:
        if context:
            self._actions = context.get("actions", {})
            self._data_sources = context.get("data_sources", {})
            self._state = context.get("state", {})
            self._view_id = context.get("view_id", "")
        if not self._visible(component):
            return ft.Container()
        component_type = component.get("component_type", component.get("type"))
        handler = self._component_handlers.get(component_type)
        if handler is None:
            raise UnsupportedComponentError(f"Unsupported component type: {component_type}")
        return handler(component)

    def _render_page(self, component: dict[str, Any]) -> ft.Control:
        return ft.Container(
            content=ft.Column(controls=[self.render(child) for child in component.get("children", [])], expand=True, scroll=ft.ScrollMode.AUTO),
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
        actions = properties.get("actions") or [self._actions[key] for key in component.get("action_keys", []) if key in self._actions]
        actions = [self._action_for(str(action.get("key", "")), action) for action in actions]
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
            key = self._field_key(child)
            if key:
                fields[key] = field
            controls.append(field)

        def submit(action: dict[str, Any]) -> None:
            values = {key: getattr(field, "value", "") or "" for key, field in fields.items()}
            payload = self._resolve_payload(dict(action.get("payload") or {}))
            if action.get("command_id"):
                payload.setdefault("command_id", action["command_id"])
            payload.update(values)
            if self._view_id:
                payload.update({"__action_key": action.get("key", ""), "__view_id": self._view_id})
            if self._view_id and isinstance(self._state.get("edit_item"), Mapping):
                payload.update({"item": self._state["edit_item"], "item_id": self._state["edit_item"].get("id")})
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
        binding = component.get("binding") or {}
        if not binding and properties.get("binding_source"):
            binding = {"source": properties.get("binding_source"), "path": properties.get("binding_path", "")}
        value = self._bound_value_for({"binding": binding}) if binding else properties.get("content", component.get("content", ""))
        return ft.Text(str(value if value is not None else ""))

    def _render_markdown(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", {})
        return ft.Markdown(str(properties.get("content", component.get("content", "")) or ""), selectable=True)

    def _render_expander(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", {})
        return ft.ExpansionTile(
            title=ft.Text(str(properties.get("title") or properties.get("label") or "Details")),
            controls=[self.render(child) for child in component.get("children", [])],
        )

    def _render_field(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", component)
        field_type = properties.get("field_type", properties.get("type", "text"))
        key = properties.get("key") or str(component.get("component_id", "")).replace("-", "_")
        label = properties.get("label", key)
        state_key = self._state_key(component, key)
        initial = self._state.get(state_key, properties.get("default", ""))
        edit_item = self._state.get("edit_item")
        field_key = self._field_key(component)
        if isinstance(edit_item, Mapping) and field_key in edit_item:
            initial = edit_item[field_key]
        if field_type == "password":
            # Secrets must never be repopulated into a client-side control.
            # An empty password is interpreted by the Core command as "keep
            # the existing secret" where that behavior is supported.
            control = ft.TextField(key=key, label=label, value="", hint_text=f"Enter {label.lower()}", password=True, can_reveal_password=True)
            control.on_change = lambda event, state_key=state_key, control=control: self._state_changed(state_key, getattr(event, "control", control).value, field_type)
            return control
        if field_type == "textarea":
            return ft.TextField(key=key, label=label, value=str(initial or ""), hint_text=f"Enter {label.lower()}", multiline=True, min_lines=4)
        if field_type == "checkbox":
            control = ft.Checkbox(label=label, value=bool(initial))
            control.on_change = lambda event, state_key=state_key, control=control: self._state_changed(state_key, getattr(event, "control", control).value, field_type)
            return control
        if field_type == "select":
            options = self._field_options(properties)
            control = ft.Dropdown(label=label, value=str(initial or options[0]) if options else None, options=[ft.DropdownOption(key=str(option), text=str(option)) for option in options])
        elif field_type == "multiselect":
            options = self._field_options(properties)
            selected = {str(value) for value in (initial or [])} if isinstance(initial, (list, tuple, set)) else set()
            checkboxes: list[ft.Control] = [ft.Text(label)]
            for option in options:
                option_value = str(option)
                checkbox = ft.Checkbox(label=option_value, value=option_value in selected)

                def on_check(event: ft.ControlEvent, *, option_value: str = option_value) -> None:
                    if getattr(event.control, "value", False):
                        selected.add(option_value)
                    else:
                        selected.discard(option_value)
                    self._state_changed(state_key, list(selected), field_type)

                checkbox.on_change = on_check
                checkboxes.append(checkbox)
            return ft.Column(controls=checkboxes, spacing=4)
        else:
            control = ft.TextField(key=key, label=label, value=str(initial or ""), hint_text=f"Enter {label.lower()}", multiline=field_type == "textarea", min_lines=4 if field_type == "textarea" else None)
        if hasattr(control, "on_change"):
            control.on_change = lambda event, state_key=state_key, field_type=field_type, control=control: self._state_changed(state_key, getattr(event, "control", control).value, field_type)
        if hasattr(control, "on_select"):
            control.on_select = lambda event, state_key=state_key, field_type=field_type, control=control: self._state_changed(state_key, getattr(event, "control", control).value, field_type)
        return control

    def _render_actions(self, component: dict[str, Any]) -> ft.Control:
        action_keys = component.get("action_keys") or []

        def button_for(action_key: str) -> ft.Control:
            action = self._action_for(action_key, component)

            def on_click(event: ft.ControlEvent) -> None:
                del event
                action_payload = self._resolve_payload(dict(action.get("payload") or component.get("payload") or {}))
                if action.get("command_id"):
                    action_payload.setdefault("command_id", action["command_id"])
                action_payload.update({"__action_key": action.get("key", action_key), "__view_id": self._view_id})
                self._on_intent(action_payload)

            return ft.Button(str(action.get("label") or action_key or "Action"), on_click=on_click)

        if action_keys:
            return ft.Row(controls=[button_for(str(action_key)) for action_key in action_keys], spacing=8)

        def on_click(event: ft.ControlEvent) -> None:
            del event
            action = component
            payload = self._resolve_payload(
                dict(action.get("payload") or component.get("payload") or {}),
                item=self._item_context,
            )
            if action.get("command_id"):
                payload.setdefault("command_id", action["command_id"])
            payload.update({"__action_key": action.get("key", ""), "__view_id": self._view_id})
            self._on_intent(payload)

        properties = component.get("properties", component)
        label = properties.get("label", "Action")
        return ft.Button(label, on_click=on_click)

    def _render_notice(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties", component)
        return ft.Container(content=ft.Text(properties.get("message", "")), padding=ft.Padding(12, 12, 12, 12))

    def _visible(self, component: dict[str, Any]) -> bool:
        condition = component.get("visible_when")
        if not condition:
            return True
        if isinstance(condition, str):
            return bool(self._condition_value(condition))
        operands = condition.get("operands", [])
        if len(operands) < 2:
            return True
        values = [self._condition_value(value) for value in operands]
        operator = condition.get("operator")
        if operator == "equals":
            return values[0] == values[1]
        if operator == "not_equals":
            return values[0] != values[1]
        if operator == "truthy":
            return bool(values[0])
        if operator == "falsy":
            return not values[0]
        if operator == "in":
            return values[0] in values[1]
        if operator == "not_in":
            return values[0] not in values[1]
        return True

    def _condition_value(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("$state."):
            return self._state.get(value.removeprefix("$state."))
        return value

    def _render_collection(self, component: dict[str, Any]) -> ft.Control:
        # A collection is often a binding/layout wrapper around a child table.
        # Let the child consume the same source instead of rendering blank
        # wrapper rows when the wrapper has no columns of its own.
        if component.get("children"):
            binding = component.get("binding") or {}
            items = self._data_sources.get(binding.get("source"), [])
            if binding.get("path"):
                items = self._value_at_path(items, binding["path"])
            if not items:
                return ft.Text((component.get("properties") or {}).get("empty_state", "No items yet."))
            controls: list[ft.Control] = []
            previous_item = self._item_context
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                self._item_context = item
                controls.append(ft.Card(content=ft.Container(content=ft.Column(
                    [self.render(child) for child in component["children"]], spacing=8
                ), padding=ft.Padding(12, 12, 12, 12))))
            self._item_context = previous_item
            return ft.Column(controls=controls, expand=True, scroll=ft.ScrollMode.AUTO)
        properties = component.get("properties", {})
        binding = component.get("binding") or {}
        items = self._data_sources.get(binding.get("source"), [])
        if binding.get("path"):
            items = self._value_at_path(items, binding["path"])
        if not items:
            return ft.Container(content=ft.Text(properties.get("empty_state", "No items yet.")), padding=ft.Padding(12, 12, 12, 12))
        columns = [column for column in properties.get("columns", []) if isinstance(column, Mapping)]
        action_keys = component.get("action_keys") or properties.get("item_action_keys") or []
        controls: list[ft.Control] = []
        if columns:
            controls.append(ft.Row([ft.Text(str(column.get("label") or column.get("key")), weight=ft.FontWeight.BOLD, expand=True) for column in columns]))
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            cells = [ft.Text(str(self._value_at_path(item, str(column.get("key") or "")) or "-"), expand=True) for column in columns]
            buttons = [self._item_action_button(key, dict(item), index) for key in action_keys if key in self._actions]
            controls.append(ft.Row(cells + buttons, spacing=8))
            controls.append(ft.Divider(height=1))
        return ft.Container(content=ft.Column(controls=controls, scroll=ft.ScrollMode.AUTO), padding=ft.Padding(12, 12, 12, 12), expand=True)

    def _item_action_button(self, key: str, item: dict[str, Any], index: int) -> ft.Control:
        action = self._action_for(key)
        def on_click(_event: ft.ControlEvent) -> None:
            payload = self._resolve_payload(dict(action.get("payload") or {}), item=item)
            if action.get("command_id"):
                payload.setdefault("command_id", action["command_id"])
            payload.update({"item": item, "item_id": item.get("id"), "__action_key": key, "__view_id": self._view_id})
            self._on_intent(payload)
        return ft.Button(str(action.get("label") or key), on_click=on_click, key=f"{self._view_id}:{key}:{item.get('id', index)}")

    def _render_columns(self, component: dict[str, Any]) -> ft.Control:
        return ft.Row(controls=[self.render(child) for child in component.get("children", [])], spacing=16)

    def _render_timeline(self, component: dict[str, Any]) -> ft.Control:
        items = self._bound_value_for(component)
        if not items:
            return ft.Text("No messages yet.")
        controls: list[ft.Control] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            speaker = item.get("speaker_name") or item.get("speaker") or ("You" if item.get("turn_kind") == "user" else "Assistant")
            message = item.get("text") or item.get("content") or ""
            controls.append(ft.Card(content=ft.Container(content=ft.Column([
                ft.Text(str(speaker), weight=ft.FontWeight.BOLD),
                ft.Text(str(message)),
            ], spacing=6), padding=ft.Padding(12, 12, 12, 12))))
        return ft.Column(controls=controls, scroll=ft.ScrollMode.AUTO, expand=True)

    def _render_navigation(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties") or {}
        items = self._data_sources.get(properties.get("binding_source"), [])
        if properties.get("binding_path"):
            items = self._value_at_path(items, properties["binding_path"])
        if not items:
            return ft.Text("No contacts available.")
        buttons: list[ft.Control] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            label = str(item.get("title") or item.get("name") or item.get("id") or "Contact")
            count = item.get("task_count")

            def select(_event: ft.ControlEvent, item: Mapping[str, Any] = item) -> None:
                value = item.get("id")
                self._state["selected_contact_id"] = value
                self._on_intent({"__view_id": self._view_id, "__state_update": {"selected_contact_id": value}})

            buttons.append(ft.Button(f"{label} ({count})" if count is not None else label, on_click=select))
        return ft.Column(controls=buttons, spacing=8, scroll=ft.ScrollMode.AUTO)

    def _render_tabs(self, component: dict[str, Any]) -> ft.Control:
        properties = component.get("properties") or {}
        tab_names = [str(value) for value in properties.get("tabs", [])]
        selected = str(self._state.get("selected_tab") or (tab_names[0] if tab_names else ""))
        buttons: list[ft.Control] = []
        for tab_name in tab_names:
            def select(_event: ft.ControlEvent, tab_name: str = tab_name) -> None:
                self._state["selected_tab"] = tab_name
                self._on_intent({"__view_id": self._view_id, "__state_update": {"selected_tab": tab_name}})

            buttons.append(ft.Button(tab_name, on_click=select))
        active_index = tab_names.index(selected) if selected in tab_names else 0
        children = component.get("children", [])
        active = self.render(children[active_index]) if children and active_index < len(children) else ft.Container()
        return ft.Column(controls=[ft.Row(controls=buttons, spacing=8), active], expand=True)

    def _render_terminal(self, component: dict[str, Any]) -> ft.Control:
        value = self._bound_value_for(component)
        lines: list[str] = []
        if isinstance(value, str) and value:
            lines = value.splitlines()
        elif isinstance(value, (list, tuple)):
            lines = [str(line) for line in value]
        elif self._item_context is not None:
            lines = self._event_lines(self._item_context.get("events", []))
        elif isinstance(self._data_sources.get("current_task"), Mapping):
            lines = self._event_lines(self._data_sources["current_task"].get("events", []))
        content = "\n".join(lines) if lines else "No loop output yet."
        return ft.Container(content=ft.Text(content, font_family="monospace", selectable=True), bgcolor=ft.Colors.BLACK, padding=ft.Padding(12, 12, 12, 12), expand=True)

    def _render_checklist(self, component: dict[str, Any]) -> ft.Control:
        value = self._bound_value_for(component)
        items = value if isinstance(value, (list, tuple)) else []
        controls: list[ft.Control] = []
        for item in items:
            if isinstance(item, Mapping):
                label = str(item.get("label") or item.get("title") or item.get("text") or "Item")
                done = bool(item.get("done") or item.get("completed"))
            else:
                label, done = str(item), False
            controls.append(ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED), ft.Text(label)]))
        return ft.Column(controls=controls or [ft.Text("No checklist items.")], spacing=4)

    def _render_progress(self, component: dict[str, Any]) -> ft.Control:
        value = self._bound_value_for(component)
        progress = 0.0
        if isinstance(value, Mapping):
            progress = float(value.get("value", value.get("completed", 0)) or 0)
            total = float(value.get("total", 0) or 0)
            if total:
                progress /= total
        elif isinstance(value, (int, float)):
            progress = float(value)
        progress = max(0.0, min(1.0, progress if progress <= 1 else progress / 100))
        return ft.ProgressBar(value=progress)

    def _render_tree(self, component: dict[str, Any]) -> ft.Control:
        value = self._bound_value_for(component)
        items = value if isinstance(value, (list, tuple)) else []
        controls = [ft.Text(str(item.get("path") or item.get("name") or item)) if isinstance(item, Mapping) else ft.Text(str(item)) for item in items]
        return ft.Column(controls=controls or [ft.Text("No files available.")], spacing=4, scroll=ft.ScrollMode.AUTO)

    @staticmethod
    def _event_lines(events: Any) -> list[str]:
        lines: list[str] = []
        for index, event in enumerate(events if isinstance(events, (list, tuple)) else [], start=1):
            if not isinstance(event, Mapping):
                continue
            event_type = str(event.get("event_type") or event.get("type") or "EVENT").replace("_", " ").upper()
            payload = event.get("payload") or {}
            lines.append(f"{index:02d} {event_type}")
            if isinstance(payload, Mapping):
                text = payload.get("final_text") or payload.get("text") or payload.get("summary")
                if text:
                    lines.append(str(text))
        return lines

    def _render_message(self, component: dict[str, Any]) -> ft.Control:
        return ft.Text(str((component.get("properties") or {}).get("text") or ""))

    def _render_status(self, component: dict[str, Any]) -> ft.Control:
        return ft.Text(str(self._bound_value_for(component) or ""), color=ft.Colors.GREEN)

    def _bound_value_for(self, component: dict[str, Any]) -> Any:
        binding = component.get("binding") or {}
        if not binding:
            properties = component.get("properties") or {}
            binding = {"source": properties.get("binding_source"), "path": properties.get("binding_path", "")}
        if self._item_context is not None and binding.get("source") in {"tasks", "contacts"}:
            value = self._item_context
        else:
            value = self._data_sources.get(binding.get("source"), [])
        return self._value_at_path(value, binding.get("path", "")) if binding.get("path") else value

    def _field_options(self, properties: Mapping[str, Any]) -> list[Any]:
        source = properties.get("binding_source")
        if source:
            values = self._data_sources.get(source, [])
            if isinstance(values, Mapping):
                values = values.get("items", values.get("agents", values.get("discussions", [])))
            if isinstance(values, (list, tuple)):
                return [item.get("id", item.get("discussion_id", item)) if isinstance(item, Mapping) else item for item in values]
        return list(properties.get("options") or [])

    def _state_key(self, component: Mapping[str, Any], key: str) -> str:
        explicit = component.get("state_key") or (component.get("properties") or {}).get("state_key")
        if explicit:
            return str(explicit)
        return {
            "agent_select": "selected_agent_id",
            "agent_select_field": "selected_agent_id",
            "discussion_select": "selected_discussion_id",
            "discussion_select_field": "selected_discussion_id",
            "chat_mode_select": "chat_mode",
            "chat_mode_select_field": "chat_mode",
            "pause_toggle": "is_chat_paused",
            "pause_toggle_field": "is_chat_paused",
            "message_input": "message_input",
            "participant_multiselect": "participant_selection",
            "participant_multiselect_field": "participant_selection",
            "task_title_field": "task_title",
            "task_prompt_field": "task_prompt",
            "max_turns_field": "max_turns",
        }.get(key, key)

    @staticmethod
    def _field_key(component: Mapping[str, Any]) -> str:
        properties = component.get("properties") or {}
        explicit = properties.get("key")
        if explicit:
            return str(explicit)
        component_id = str(component.get("component_id") or "")
        normalized = component_id.replace("_", "-")
        for prefix in ("ai-host-", "agent-config-", "user-", "group-", "memory-", "pref-", "module-", "agent-", "alarm-", "tool-"):
            if normalized.startswith(prefix):
                normalized = normalized.removeprefix(prefix)
                break
        if normalized.startswith("is-"):
            normalized = "is_" + normalized.removeprefix("is-")
        parts = normalized.split("-")
        if parts and parts[-1] == "field":
            parts.pop()
        return parts[-1].replace("-", "_") if parts else "field"

    def _state_changed(self, key: str, value: Any, field_type: str) -> None:
        if field_type == "number":
            try:
                value = float(value) if value not in (None, "") else None
            except (TypeError, ValueError):
                pass
        self._state[key] = value
        if self._view_id and field_type not in {"text", "textarea", "password"}:
            self._on_intent({"__view_id": self._view_id, "__state_update": {key: value}})

    def _resolve_payload(self, value: Any, *, item: Mapping[str, Any] | None = None) -> Any:
        if isinstance(value, str):
            if value.startswith("$state."):
                return self._state.get(value.removeprefix("$state."))
            if value.startswith("$item."):
                return (item or {}).get(value.removeprefix("$item."))
            return value
        if isinstance(value, Mapping):
            return {str(key): self._resolve_payload(item_value, item=item) for key, item_value in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._resolve_payload(item_value, item=item) for item_value in value]
        return value

    def _action_for(self, key: str, declared: Mapping[str, Any] | None = None) -> dict[str, Any]:
        action = dict(self._actions.get(key, {}))
        if declared:
            action.update(dict(declared))
        if "command_id" not in action and key in self._actions:
            action["command_id"] = self._actions[key].get("command_id", "")
        return action

    @staticmethod
    def _value_at_path(value: Any, path: str) -> Any:
        current = value
        for part in [piece for piece in str(path).split(".") if piece]:
            # Collection endpoints may return either {"items": [...]} or the
            # collection itself. Treat the conventional items path as an
            # identity operation for the latter form.
            if isinstance(current, (list, tuple)) and part == "items":
                continue
            if isinstance(current, Mapping):
                if part == "items" and part not in current:
                    current = current.get("discussions", current.get("messages", current.get("agents", [])))
                else:
                    current = current.get(part)
            else:
                return None
        return current
