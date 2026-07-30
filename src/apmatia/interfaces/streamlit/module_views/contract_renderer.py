"""Streamlit renderer for serialized version 1 view documents."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from typing import Any

import streamlit as st


Intent = dict[str, Any]


def render_view_document(
    document: Mapping[str, Any],
    *,
    data_sources: Mapping[str, Any] | None = None,
    on_intent: Callable[[Intent], None] | None = None,
) -> list[Intent]:
    """Render a serialized view document and return framework-neutral intent events."""
    intents: list[Intent] = []
    sources = dict(data_sources or {})
    if int(document.get("schema_version") or 0) != 1:
        st.warning(f"Unsupported view contract version: {document.get('schema_version')}")
        return intents

    view_id = str(document.get("view_id") or "unknown-view")
    state = initialize_view_state(document)
    actions = {
        str(action.get("key") or ""): action
        for action in _mapping_sequence(document.get("actions"))
        if str(action.get("key") or "")
    }

    def emit(action: Mapping[str, Any], *, item: Any = None, payload: Mapping[str, Any] | None = None) -> None:
        event_payload = dict(action.get("payload") or {})
        command_id = str(action.get("command_id") or "").strip()
        operation = str(action.get("operation") or "").strip()
        if command_id:
            event_payload["command_id"] = command_id
        if operation:
            event_payload["operation"] = operation
        event_payload.update(dict(payload or {}))
        item_key = _document_item_key(document)
        item_id = _value_at_path(item, item_key) if item is not None else None
        intent = {
            "view_id": view_id,
            "intent": str(action.get("intent") or action.get("key") or ""),
            "action_key": str(action.get("key") or ""),
            "scope": str(action.get("scope") or "view"),
            "item_id": None if item_id is None else str(item_id),
            "item": item,
            "payload": event_payload,
        }
        intents.append(intent)
        if on_intent is not None:
            on_intent(intent)

    presentation = document.get("presentation")
    if not isinstance(presentation, Mapping):
        st.warning("This view document has no presentation tree.")
        return intents

    st.title(str(document.get("title") or view_id))
    caption = str((presentation.get("properties") or {}).get("caption") or "")
    if caption:
        st.caption(caption)
    description = str(document.get("description") or "")
    if description:
        st.write(description)

    _render_view_actions(document, actions, sources, state, emit)
    for component in _mapping_sequence(presentation.get("children")):
        _render_component(component, document, actions, sources, state, emit)
    return intents


def initialize_view_state(document: Mapping[str, Any]) -> dict[str, Any]:
    """Initialize declared semantic state without exposing Streamlit keys to the contract."""
    view_id = str(document.get("view_id") or "unknown-view")
    storage_key = f"view_contract_state:{view_id}"
    stored = st.session_state.get(storage_key)
    if not isinstance(stored, dict):
        stored = {}
        st.session_state[storage_key] = stored
    for definition in _mapping_sequence(document.get("state")):
        key = str(definition.get("key") or "")
        if key and key not in stored:
            stored[key] = definition.get("default")
    return stored


def evaluate_condition(
    condition: Mapping[str, Any] | None,
    *,
    data_sources: Mapping[str, Any],
    state: Mapping[str, Any],
    capabilities: Mapping[str, Any] | None = None,
) -> bool:
    """Evaluate the version 1 safe condition language."""
    if not condition:
        return True
    operator = str(condition.get("operator") or "")
    operands = [
        _resolve_operand(value, data_sources=data_sources, state=state, capabilities=capabilities or {})
        for value in list(condition.get("operands") or [])
    ]
    if operator == "all":
        return all(bool(value) for value in operands)
    if operator == "any":
        return any(bool(value) for value in operands)
    if operator == "not":
        return not bool(operands[0])
    if operator == "exists":
        return operands[0] is not None
    if operator == "truthy":
        return bool(operands[0])
    if operator == "falsy":
        return not bool(operands[0])
    left, right = operands
    if operator == "equals":
        return left == right
    if operator == "not_equals":
        return left != right
    if operator == "in":
        return left in right
    if operator == "not_in":
        return left not in right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    return False


def apply_effects(
    document: Mapping[str, Any],
    effects: list[Mapping[str, Any]],
    *,
    result: Any = None,
) -> bool:
    """Apply renderer-owned version 1 effects and report whether a refresh is requested."""
    state = initialize_view_state(document)
    refresh_requested = False
    for effect in effects:
        effect_type = str(effect.get("effect_type") or "")
        target = str(effect.get("target") or "")
        if effect_type in {"refresh_source", "refresh_view"}:
            refresh_requested = True
        elif effect_type == "set_state" and target:
            state[target] = _effect_value(effect, result)
        elif effect_type == "clear_state" and target:
            state.pop(target, None)
        elif effect_type == "select_item" and target:
            state[target] = _effect_value(effect, result)
        elif effect_type == "show_notification":
            value = _effect_value(effect, result)
            if value not in (None, ""):
                st.success(str(value))
        elif effect_type in {"open_panel", "start_polling"} and target:
            state[target] = True
        elif effect_type in {"close_panel", "stop_polling"} and target:
            state[target] = False
    return refresh_requested


def find_form_component(document: Mapping[str, Any], kind: str) -> Mapping[str, Any] | None:
    """Find a normalized compatibility form by its stable component suffix."""
    presentation = document.get("presentation")
    if not isinstance(presentation, Mapping):
        return None
    suffix = f":{kind}"
    for component in _walk_components(presentation):
        if str(component.get("component_type") or "") != "form":
            continue
        if str(component.get("component_id") or "").endswith(suffix):
            return component
    return None


def render_form_component(
    component: Mapping[str, Any],
    *,
    view_id: str,
    form_key_suffix: str,
    initial_values: Mapping[str, Any] | None = None,
    title: str | None = None,
    submit_label: str | None = None,
    data_sources: Mapping[str, Any] | None = None,
) -> tuple[bool, bool, dict[str, Any], str | None]:
    """Render a serialized form component for create/edit controller flows."""
    properties = component.get("properties") or {}
    resolved_title = title if title is not None else str(properties.get("title") or "")
    if resolved_title:
        st.subheader(resolved_title)
    description = str(properties.get("description") or "")
    if description:
        st.caption(description)
    payload: dict[str, Any] = {}
    selected_action: str | None = None
    with st.form(f"contract-form:{view_id}:{form_key_suffix}"):
        current_section = ""
        for field in _mapping_sequence(component.get("children")):
            if str(field.get("component_type") or "") != "field":
                continue
            field_properties = field.get("properties") or {}
            key = str(field_properties.get("key") or "")
            if not key:
                continue
            section = str(field_properties.get("section") or "")
            if section and section != current_section:
                st.subheader(section)
                current_section = section
            initial_value = None if initial_values is None else initial_values.get(key)
            payload[key] = _render_field(
                field_properties,
                initial_value=initial_value,
                data_sources=data_sources or {},
            )

        declared_actions = _mapping_sequence(properties.get("actions"))
        if declared_actions:
            columns = st.columns(len(declared_actions))
            for column, action in zip(columns, declared_actions):
                with column:
                    if st.form_submit_button(
                        str(action.get("label") or action.get("key") or "Action"),
                        type=_button_type(action),
                        use_container_width=True,
                    ):
                        selected_action = str(action.get("key") or "")
        submitted = st.form_submit_button(
            submit_label or str(properties.get("submit_label") or "Save"),
            type="primary",
            use_container_width=True,
        )
        cancel_label = str(properties.get("cancel_label") or "")
        cancelled = bool(st.form_submit_button(cancel_label)) if cancel_label else False
    return submitted, cancelled, payload, selected_action


def _render_view_actions(
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Any],
    state: Mapping[str, Any],
    emit: Callable[..., None],
) -> None:
    render_mode = str(((document.get("presentation") or {}).get("properties") or {}).get("render_mode") or "")
    visible = [
        action
        for action in actions.values()
        if str(action.get("scope") or "") == "view"
        and not (render_mode == "form" and str(action.get("intent") or "") == "save")
    ]
    if not visible:
        return
    columns = st.columns(len(visible))
    for column, action in zip(columns, visible):
        with column:
            enabled = evaluate_condition(action.get("enabled_when"), data_sources=sources, state=state)
            if st.button(
                str(action.get("label") or action.get("key") or "Action"),
                key=f"contract-view:{document.get('view_id')}:{action.get('key')}",
                type=_button_type(action),
                disabled=not enabled,
                use_container_width=True,
            ):
                emit(action)


def _render_component(
    component: Mapping[str, Any],
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Any],
    state: Mapping[str, Any],
    emit: Callable[..., None],
) -> None:
    if not evaluate_condition(component.get("visible_when"), data_sources=sources, state=state):
        return
    component_type = str(component.get("component_type") or "")
    if component_type in {"navigation", "timeline", "message", "composer", "detail", "terminal", "checklist", "progress", "tree"}:
        _render_rich_component(component, document, actions, sources, state, emit)
        return
    if component_type == "field":
        _render_bound_field(component, document, sources, state)
        return
    if component_type == "actions":
        for action_key in list(component.get("action_keys") or []):
            action = actions.get(str(action_key))
            if action is None:
                continue
            if st.button(
                str(action.get("label") or action.get("key") or "Action"),
                key=f"contract-action:{document.get('view_id')}:{action.get('key')}",
            ):
                emit(action)
        return
    if component_type in {"table", "collection"}:
        _render_collection(component, document, actions, sources, state, emit)
        return
    if component_type == "form":
        render_mode = str(((document.get("presentation") or {}).get("properties") or {}).get("render_mode") or "")
        if render_mode == "form":
            _render_form(component, document, actions, sources, state, emit)
        return
    if component_type in {"stack", "panel", "card", "columns", "tabs", "expander"}:
        for child in _mapping_sequence(component.get("children")):
            _render_component(child, document, actions, sources, state, emit)
        return
    if component_type in {"text", "markdown", "notice", "status"}:
        value = _bound_value(component, sources, state)
        text = value if value not in (None, "") else (component.get("properties") or {}).get("text")
        if text not in (None, ""):
            st.write(text)


def _render_rich_component(
    component: Mapping[str, Any],
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Any],
    state: Mapping[str, Any],
    emit: Callable[..., None],
) -> None:
    """Render rich contract components with the same generic binding rules as CRUD views."""
    component_type = str(component.get("component_type") or "")
    properties = component.get("properties") or {}
    bound = _bound_value(component, sources, state)
    if component_type == "navigation":
        items = bound if isinstance(bound, (list, tuple)) else []
        for index, item in enumerate(items):
            label = _display_value(_value_at_path(item, "title") or _value_at_path(item, "label") or item, "-")
            if st.button(str(label), key=f"contract-nav:{document.get('view_id')}:{index}", use_container_width=True):
                action_key = str((component.get("action_keys") or ["select_contact"])[0])
                if action_key in actions:
                    emit(actions[action_key], item=item)
        return
    if component_type == "timeline":
        items = bound if isinstance(bound, (list, tuple)) else []
        for item in items:
            with st.container(border=True):
                st.write(_display_value(_value_at_path(item, "text") or _value_at_path(item, "content") or item, "-"))
        return
    if component_type == "message":
        value = bound
        if value not in (None, ""):
            st.write(_display_value(_value_at_path(value, "text") or value, "-"))
        for child in _mapping_sequence(component.get("children")):
            _render_component(child, document, actions, sources, state, emit)
        return
    if component_type == "terminal":
        value = _value_at_path(bound, "output") if isinstance(bound, Mapping) else bound
        st.code(str(value or ""), language="text")
        return
    if component_type == "checklist":
        entries = bound if isinstance(bound, (list, tuple)) else []
        for entry in entries:
            if isinstance(entry, Mapping):
                label = str(entry.get("label") or entry.get("title") or entry.get("text") or "Item")
                st.checkbox(label, value=bool(entry.get("completed")), disabled=True)
            else:
                st.write(str(entry))
        return
    if component_type == "progress":
        value = bound
        if isinstance(value, Mapping):
            value = value.get("fraction", value.get("value", 0))
        try:
            numeric = float(value or 0)
            st.progress(max(0.0, min(1.0, numeric if numeric <= 1 else numeric / 100)))
        except (TypeError, ValueError):
            st.caption(str(value or ""))
        return
    if component_type == "tree":
        items = bound if isinstance(bound, (list, tuple)) else []
        for item in items:
            st.write(f"📄 {_display_value(_value_at_path(item, 'path') or item, '-')}")
        return
    if component_type == "detail":
        if isinstance(bound, Mapping):
            st.json(dict(bound))
        elif bound not in (None, ""):
            st.write(bound)
        return
    if component_type == "composer":
        for child in _mapping_sequence(component.get("children")):
            _render_component(child, document, actions, sources, state, emit)


def _render_bound_field(
    component: Mapping[str, Any],
    document: Mapping[str, Any],
    sources: Mapping[str, Any],
    state: dict[str, Any],
) -> None:
    properties = component.get("properties") or {}
    key = str(properties.get("key") or component.get("component_id") or "")
    label = str(properties.get("label") or key)
    widget_key = f"contract-field:{document.get('view_id')}:{component.get('component_id') or key}"
    initial = state.get(key, properties.get("default"))
    field_type = str(properties.get("field_type") or "text")
    if field_type == "select":
        source = sources.get(str(properties.get("binding_source") or ""), [])
        options = list(source) if isinstance(source, (list, tuple)) else list(properties.get("options") or [])
        if options:
            values = [item.get("value", item) if isinstance(item, Mapping) else item for item in options]
            state[key] = st.selectbox(label, values, key=widget_key, index=max(0, values.index(initial)) if initial in values else 0)
    elif field_type == "multiselect":
        source = sources.get(str(properties.get("binding_source") or ""), [])
        options = list(source) if isinstance(source, (list, tuple)) else list(properties.get("options") or [])
        values = [item.get("value", item) if isinstance(item, Mapping) else item for item in options]
        selected = initial if isinstance(initial, list) else []
        state[key] = st.multiselect(label, values, default=[item for item in selected if item in values], key=widget_key)
    elif field_type == "checkbox":
        state[key] = st.checkbox(label, value=bool(initial), key=widget_key)
    elif field_type == "number":
        state[key] = st.number_input(label, value=float(initial or 0), min_value=float(properties.get("min_value", 0)), step=float(properties.get("step", 1)), key=widget_key)
    else:
        state[key] = st.text_area(label, value=str(initial or ""), key=widget_key) if field_type == "textarea" else st.text_input(label, value=str(initial or ""), key=widget_key)


def _render_collection(
    component: Mapping[str, Any],
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Any],
    state: Mapping[str, Any],
    emit: Callable[..., None],
) -> None:
    items = _bound_value(component, sources, state)
    if not isinstance(items, (list, tuple)) or not items:
        st.info(str((component.get("properties") or {}).get("empty_state") or "No items yet."))
        return
    properties = component.get("properties") or {}
    columns = [entry for entry in list(properties.get("columns") or []) if isinstance(entry, Mapping)]
    action_keys = [str(key) for key in list(properties.get("item_action_keys") or component.get("action_keys") or [])]
    item_actions = [actions[key] for key in action_keys if key in actions]
    if columns or item_actions:
        headers = st.columns(len(columns) + (1 if item_actions else 0))
        for index, column in enumerate(columns):
            with headers[index]:
                st.caption(str(column.get("label") or column.get("key") or ""))
        if item_actions:
            with headers[-1]:
                st.caption("Actions")
    item_key = str(properties.get("item_key") or "id")
    for row_index, item in enumerate(items):
        with st.container(border=True):
            cells = st.columns(len(columns) + (1 if item_actions else 0)) if columns else []
            for index, column in enumerate(columns):
                with cells[index]:
                    value = _value_at_path(item, str(column.get("key") or ""))
                    st.write(_display_value(value, str(column.get("empty_value") or "-")))
            action_container = cells[-1] if cells and item_actions else None
            if not columns:
                st.write(_display_value(item, "-"))
            if item_actions:
                context = action_container if action_container is not None else st.container()
                with context:
                    buttons = st.columns(len(item_actions))
                    for button_column, action in zip(buttons, item_actions):
                        with button_column:
                            enabled = evaluate_condition(action.get("enabled_when"), data_sources={**sources, "item": item}, state=state)
                            if st.button(
                                str(action.get("label") or action.get("key") or "Action"),
                                key=f"contract-item:{document.get('view_id')}:{_value_at_path(item, item_key) or row_index}:{action.get('key')}",
                                type=_button_type(action),
                                disabled=not enabled,
                                use_container_width=True,
                            ):
                                emit(action, item=item)


def _render_form(
    component: Mapping[str, Any],
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Any],
    state: Mapping[str, Any],
    emit: Callable[..., None],
) -> None:
    properties = component.get("properties") or {}
    form_actions = [
        action for action in actions.values() if str(action.get("scope") or "") in {"form", "view"}
    ]
    submit_action = next((action for action in form_actions if str(action.get("intent") or "") == "save"), None)
    if submit_action is None:
        st.warning("This form view has no submit action.")
        return
    submitted, _cancelled, payload, _selected_action = render_form_component(
        component,
        view_id=str(document.get("view_id") or "unknown-view"),
        form_key_suffix=str(properties.get("key") or component.get("component_id") or "form"),
        title=(
            ""
            if str(properties.get("title") or "") == str(document.get("title") or "")
            else str(properties.get("title") or "")
        ),
        submit_label=str(properties.get("submit_label") or submit_action.get("label") or "Save"),
        data_sources=sources,
    )
    if submitted:
        emit(submit_action, payload=payload)


def _render_field(
    field: Mapping[str, Any],
    *,
    initial_value: Any = None,
    data_sources: Mapping[str, Any] | None = None,
) -> Any:
    label = str(field.get("label") or field.get("key") or "Field")
    field_type = str(field.get("field_type") or "text").lower()
    value = initial_value if initial_value not in (None, "") else field.get("default")
    help_text = str(field.get("help_text") or "") or None
    placeholder = str(field.get("placeholder") or "")
    if field_type == "textarea":
        return st.text_area(label, value=_string_value(value), placeholder=placeholder, help=help_text)
    if field_type == "number":
        number = value if isinstance(value, (int, float)) else 0
        return st.number_input(label, value=number, min_value=field.get("min_value"), max_value=field.get("max_value"), step=field.get("step"), help=help_text)
    if field_type == "checkbox":
        return st.checkbox(label, value=bool(value), help=help_text)
    if field_type == "color":
        return st.color_picker(label, value=_string_value(value) or "#000000", help=help_text)
    if field_type == "slider":
        return st.slider(label, min_value=field.get("min_value"), max_value=field.get("max_value"), value=value, step=field.get("step"), help=help_text)
    if field_type in {"select", "multiselect"}:
        options = list(field.get("options") or [])
        option_binding = field.get("options_source")
        if isinstance(option_binding, Mapping):
            source = str(option_binding.get("source") or "")
            bound_options = (data_sources or {}).get(source, option_binding.get("default", []))
            if isinstance(bound_options, (list, tuple)):
                options = list(bound_options)
        labels = [_option_label(option) for option in options]
        values = [_option_value(option) for option in options]
        if field_type == "multiselect":
            selected = st.multiselect(label, labels, default=[_option_label(item) for item in list(value or [])], help=help_text)
            return [values[labels.index(item)] for item in selected]
        selected_index = values.index(value) if value in values else 0
        selected = st.selectbox(label, labels, index=selected_index, help=help_text) if labels else ""
        return values[labels.index(selected)] if selected in labels else selected
    if field_type == "date":
        return st.date_input(label, value=_date_value(value), help=help_text)
    if field_type == "time":
        return st.time_input(label, value=_time_value(value), help=help_text)
    if field_type == "datetime":
        return datetime.combine(st.date_input(f"{label} date", value=_date_value(value)), st.time_input(f"{label} time", value=_time_value(value)))
    if field_type == "file":
        return st.file_uploader(label, help=help_text)
    if field_type == "hidden":
        return value
    return st.text_input(label, value=_string_value(value), placeholder=placeholder, type="password" if field_type == "password" else "default", help=help_text)


def _bound_value(component: Mapping[str, Any], sources: Mapping[str, Any], state: Mapping[str, Any]) -> Any:
    binding = component.get("binding")
    if not isinstance(binding, Mapping):
        return None
    source = str(binding.get("source") or "")
    root = state.get(source) if source in state else sources.get(source, binding.get("default"))
    return _value_at_path(root, str(binding.get("path") or ""))


def _resolve_operand(value: Any, *, data_sources: Mapping[str, Any], state: Mapping[str, Any], capabilities: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping) and "operator" in value:
        return evaluate_condition(value, data_sources=data_sources, state=state, capabilities=capabilities)
    if isinstance(value, Mapping) and "source" in value:
        source = str(value.get("source") or "")
        roots = capabilities if source == "capabilities" else state if source in state else data_sources
        root = roots if source == "capabilities" else roots.get(source, value.get("default"))
        return _value_at_path(root, str(value.get("path") or ""))
    return value


def _value_at_path(value: Any, path: str) -> Any:
    current = value
    for part in [item for item in path.split(".") if item]:
        if isinstance(current, Mapping):
            current = current.get(part)
        elif isinstance(current, (list, tuple)) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            current = getattr(current, part, None)
        if current is None:
            break
    return current


def _effect_value(effect: Mapping[str, Any], result: Any) -> Any:
    source = str(effect.get("source") or "")
    if source.startswith("result"):
        return _value_at_path(result, source.removeprefix("result").lstrip("."))
    return effect.get("value")


def _document_item_key(document: Mapping[str, Any]) -> str:
    for source in _mapping_sequence(document.get("data_sources")):
        if str(source.get("kind") or "") == "collection":
            return str(source.get("item_key") or "id")
    return "id"


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in list(value or []) if isinstance(item, Mapping)]


def _walk_components(component: Mapping[str, Any]):
    yield component
    for child in _mapping_sequence(component.get("children")):
        yield from _walk_components(child)


def _button_type(action: Mapping[str, Any]) -> str:
    style = str(action.get("style") or "secondary")
    return style if style in {"primary", "secondary"} else "secondary"


def _display_value(value: Any, empty: str) -> str:
    if value in (None, ""):
        return empty
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _string_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _option_label(option: Any) -> str:
    return str(option.get("label") or option.get("name") or option.get("value") or "") if isinstance(option, Mapping) else str(option)


def _option_value(option: Any) -> Any:
    if isinstance(option, Mapping):
        return option.get("value", option.get("id", option.get("key", _option_label(option))))
    return option


def _date_value(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return datetime.now().astimezone().date()


def _time_value(value: Any) -> time:
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value:
        try:
            return time.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.now().astimezone().time().replace(microsecond=0, tzinfo=None)
