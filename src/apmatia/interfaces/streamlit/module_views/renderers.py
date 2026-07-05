from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Mapping

import streamlit as st

from apmatia.interfaces.streamlit.module_views.models import (
    CollectionViewDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewIntent,
)


def render_module_view(
    spec: CollectionViewDescriptor,
    *,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> list[ModuleViewIntent]:
    intents: list[ModuleViewIntent] = []

    def emit(intent: ModuleViewIntent) -> None:
        intents.append(intent)
        if on_intent is not None:
            on_intent(intent)

    if not spec.is_supported:
        render_unsupported_view(spec)
        return intents

    render_view_header(spec, on_intent=emit)
    render_collection_view(spec, on_intent=emit)
    return intents


def render_view_header(
    spec: CollectionViewDescriptor,
    *,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    st.title(spec.title)
    if spec.caption:
        st.caption(spec.caption)
    if spec.description:
        st.write(spec.description)

    if not spec.view_actions:
        return

    action_columns = st.columns(len(spec.view_actions))
    for column, action in zip(action_columns, spec.view_actions):
        with column:
            if _button(action, key_prefix=f"view-{spec.view_id}", disabled=False):
                _emit_view_intent(spec, action, item=None, on_intent=on_intent)


def render_collection_view(
    spec: CollectionViewDescriptor,
    *,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    if not spec.items:
        st.info(spec.empty_state)
        return

    header_columns = [column.label for column in spec.columns]
    has_actions = bool(spec.item_actions)
    if header_columns or has_actions:
        table_columns = list(st.columns(len(header_columns) + (1 if has_actions else 0)))
        for index, label in enumerate(header_columns):
            with table_columns[index]:
                st.caption(label)
        if has_actions:
            with table_columns[-1]:
                st.caption("Actions")

    for index, item in enumerate(spec.items):
        with st.container(border=True):
            render_collection_row(spec, item, row_index=index, on_intent=on_intent)

    troubleshooting_items = _troubleshooting_items(spec.items)
    if troubleshooting_items:
        st.subheader("Troubleshooting")
        for index, item in enumerate(troubleshooting_items):
            with st.container(border=True):
                summary = str(_item_value(item, "host_summary") or _item_value(item, spec.item_key) or f"Row {index + 1}").strip()
                error = str(_item_value(item, "resource_error") or "").strip()
                hint = str(_item_value(item, "troubleshooting_hint") or "").strip()
                connection_test = str(_item_value(item, "ssh_connection_test_command") or "").strip()
                install_command = str(_item_value(item, "ssh_public_key_install_command") or "").strip()
                resource_probe = str(_item_value(item, "ssh_resource_probe_command") or "").strip()
                if summary:
                    st.write(summary)
                if hint:
                    st.write(hint)
                if error:
                    st.write(error)
                if connection_test:
                    st.caption("Copy and run this from the machine running Apmatia to inspect the SSH handshake.")
                    st.code(connection_test, language="bash")
                if install_command:
                    st.caption("Copy and run this from the machine running Apmatia after the key has been created.")
                    st.code(install_command, language="bash")
                if resource_probe:
                    st.caption("Copy and run this exact probe from the machine running Apmatia to reproduce the resource check.")
                    st.code(resource_probe, language="bash")


def render_collection_row(
    spec: CollectionViewDescriptor,
    item: Any,
    *,
    row_index: int,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    if spec.columns:
        row_columns = st.columns(len(spec.columns) + (1 if spec.item_actions else 0))
        for index, column in enumerate(spec.columns):
            with row_columns[index]:
                st.write(_format_item_value(item, column.key, column.empty_value))
        if spec.item_actions:
            with row_columns[-1]:
                _render_item_actions(spec, item, row_index=row_index, on_intent=on_intent)
        return

    st.write(_summarize_item(item))
    if spec.item_actions:
        _render_item_actions(spec, item, row_index=row_index, on_intent=on_intent)


def render_unsupported_view(spec: CollectionViewDescriptor) -> None:
    st.title(spec.title)
    if spec.caption:
        st.caption(spec.caption)
    message = spec.unsupported_reason or "This module view cannot be rendered by the current adapter."
    st.warning(message)


def render_module_view_form(
    form: ModuleViewFormDescriptor,
    *,
    form_key: str,
    title: str | None = None,
    submit_label: str | None = None,
    initial_values: Mapping[str, Any] | None = None,
) -> tuple[bool, bool, dict[str, Any], str | None]:
    st.subheader(title or form.title)
    if form.description:
        st.caption(form.description)

    payload: dict[str, Any] = {}
    action_key: str | None = None
    with st.form(form_key):
        for field in form.fields:
            payload[field.key] = _render_form_field(field, initial_value=None if initial_values is None else initial_values.get(field.key))
        if form.actions:
            action_columns = st.columns(len(form.actions))
            for column, action in zip(action_columns, form.actions):
                with column:
                    if _form_button(action):
                        action_key = action.key
        submitted = st.form_submit_button(submit_label or form.submit_label)
        cancelled = bool(st.form_submit_button(form.cancel_label)) if form.cancel_label else False
    return submitted, cancelled, payload, action_key


def _render_item_actions(
    spec: CollectionViewDescriptor,
    item: Any,
    *,
    row_index: int,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    if not spec.item_actions:
        return

    action_columns = st.columns(len(spec.item_actions))
    for column, action in zip(action_columns, spec.item_actions):
        with column:
            item_key = _item_key(item, spec.item_key, row_index=row_index)
            if _button(action, key_prefix=f"{spec.view_id}-{item_key}", disabled=False):
                _emit_item_intent(spec, action, item=item, on_intent=on_intent)


def _emit_view_intent(
    spec: CollectionViewDescriptor,
    action: ModuleViewActionDescriptor,
    *,
    item: Any | None,
    on_intent: Callable[[ModuleViewIntent], None] | None,
) -> None:
    intent = ModuleViewIntent(
        view_id=spec.view_id,
        intent=action.intent,
        action_key=action.key,
        scope=action.scope,
        item_id=None if item is None else _item_id(item, spec.item_key),
        item=item,
        payload=dict(action.payload),
    )
    if on_intent is not None:
        on_intent(intent)


def _emit_item_intent(
    spec: CollectionViewDescriptor,
    action: ModuleViewActionDescriptor,
    *,
    item: Any,
    on_intent: Callable[[ModuleViewIntent], None] | None,
) -> None:
    _emit_view_intent(spec, action, item=item, on_intent=on_intent)


def _button(action: ModuleViewActionDescriptor, *, key_prefix: str, disabled: bool) -> bool:
    button_type = action.style if action.style in {"primary", "secondary"} else "secondary"
    return st.button(
        action.label,
        key=f"{key_prefix}-{action.key}",
        type=button_type,
        disabled=disabled,
        use_container_width=True,
    )


def _form_button(action: ModuleViewFormActionDescriptor) -> bool:
    button_type = action.style if action.style in {"primary", "secondary"} else "secondary"
    return st.form_submit_button(action.label, type=button_type, use_container_width=True)


def _render_form_field(field: ModuleViewFormFieldDescriptor, *, initial_value: Any = None) -> Any:
    field_type = field.field_type.lower().strip()
    value = initial_value if initial_value not in (None, "") else field.default
    common_kwargs = {
        "help": field.help_text or None,
    }

    if field_type == "textarea":
        return st.text_area(
            field.label,
            value=_stringify_form_value(value),
            placeholder=field.placeholder,
            **common_kwargs,
        )
    if field_type == "number":
        number_value = value if isinstance(value, (int, float)) else field.default if isinstance(field.default, (int, float)) else 0
        return st.number_input(
            field.label,
            value=number_value,
            min_value=field.min_value,
            max_value=field.max_value,
            step=field.step,
            **common_kwargs,
        )
    if field_type == "checkbox":
        return st.checkbox(
            field.label,
            value=bool(value),
            help=field.help_text or None,
        )
    if field_type == "select":
        options = list(field.options)
        if not options:
            return ""
        default_value = str(value) if value not in (None, "") else str(field.default) if field.default not in (None, "") else options[0]
        try:
            index = options.index(default_value)
        except ValueError:
            index = 0
        return st.selectbox(
            field.label,
            options,
            index=index,
            help=field.help_text or None,
        )
    if field_type == "password":
        return st.text_input(
            field.label,
            value=_stringify_form_value(value),
            placeholder=field.placeholder,
            type="password",
            **common_kwargs,
        )

    return st.text_input(
        field.label,
        value=_stringify_form_value(value),
        placeholder=field.placeholder,
        **common_kwargs,
    )


def _stringify_form_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _format_item_value(item: Any, key: str, empty_value: str) -> str:
    value = _item_value(item, key)
    if value is None or value == "":
        return empty_value
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _summarize_item(item: Any) -> str:
    if isinstance(item, dict):
        return json.dumps(item, ensure_ascii=False, default=str)
    return str(item)


def _item_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _item_id(item: Any, key: str) -> str | None:
    value = _item_value(item, key)
    if value is None:
        return None
    return str(value)


def _item_key(item: Any, key: str, *, row_index: int) -> str:
    item_id = _item_id(item, key)
    if item_id:
        return item_id
    return f"row-{row_index}"


def _troubleshooting_items(items: tuple[Any, ...]) -> list[Any]:
    matches: list[Any] = []
    for item in items:
        error = _item_value(item, "resource_error")
        if error is None:
            continue
        if str(error).strip():
            matches.append(item)
    return matches
