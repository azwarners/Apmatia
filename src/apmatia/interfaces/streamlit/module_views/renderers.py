from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

from apmatia.interfaces.streamlit.module_views.models import (
    CollectionViewDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewNavigationPaneDescriptor,
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

    if spec.view_id == "agent_config.agent_config.view":
        render_agent_config_view(spec, on_intent=emit)
        return intents

    if spec.render_mode == "form":
        render_form_view(spec, on_intent=emit)
        return intents

    render_view_header(spec, on_intent=emit)
    render_collection_view(spec, on_intent=emit)
    return intents


def render_form_view(
    spec: CollectionViewDescriptor,
    *,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    st.title(spec.title)
    if spec.caption:
        st.caption(spec.caption)
    if spec.description:
        st.write(spec.description)

    form = spec.edit_form
    save_action = next((action for action in spec.view_actions if action.intent == "save"), None)
    if form is None or save_action is None:
        st.warning("This form view is missing its form schema or save action.")
        return

    initial_values = spec.items[0] if spec.items and isinstance(spec.items[0], Mapping) else None
    submitted, _cancelled, payload, _action_key = render_module_view_form(
        form,
        form_key=f"module_view_form:{spec.view_id}:{form.key}",
        initial_values=initial_values,
    )
    if submitted and on_intent is not None:
        on_intent(
            ModuleViewIntent(
                view_id=spec.view_id,
                intent=save_action.intent,
                action_key=save_action.key,
                scope=save_action.scope,
                item_id=None,
                item=initial_values,
                payload={**dict(save_action.payload), **payload},
            )
        )


def render_agent_config_view(
    spec: CollectionViewDescriptor,
    *,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> None:
    st.title(spec.title)
    if spec.caption:
        st.caption(spec.caption)
    if spec.description:
        st.write(spec.description)

    if not spec.items:
        st.info(spec.empty_state)
        return

    st.info("Knowledge roots can be shared across agents. Workspace roots are usually unique per agent.")

    agent_options = [item for item in spec.items if _item_id(item, spec.item_key) is not None]
    if not agent_options:
        st.info(spec.empty_state)
        return

    save_action = next((action for action in spec.view_actions if action.intent == "save"), None)
    if save_action is None:
        st.warning("This agent config view is missing a save action.")
        return

    selected_agent_state_key = f"agent_config_selected_agent_id:{spec.view_id}"
    selected_agent_id = str(st.session_state.get(selected_agent_state_key) or "").strip()
    agent_id_strings = {str(_item_id(item, spec.item_key) or "").strip() for item in agent_options}
    if selected_agent_id not in agent_id_strings:
        selected_agent_id = str(_item_id(agent_options[0], spec.item_key) or "").strip()
        st.session_state[selected_agent_state_key] = selected_agent_id

    selected_agent = next((item for item in agent_options if str(_item_id(item, spec.item_key) or "").strip() == selected_agent_id), agent_options[0])
    selected_agent_id = str(_item_id(selected_agent, spec.item_key) or "").strip()
    st.session_state[selected_agent_state_key] = selected_agent_id

    agent_label = lambda item: str(_item_value(item, "name") or _item_id(item, spec.item_key) or "Agent")
    selected_agent = st.selectbox(
        "Agent",
        options=agent_options,
        index=_selected_selectbox_index(agent_options, selected_agent_id, spec.item_key),
        format_func=agent_label,
        help="Choose the agent whose roots you want to configure.",
    )
    selected_agent_id = str(_item_id(selected_agent, spec.item_key) or "").strip()
    st.session_state[selected_agent_state_key] = selected_agent_id

    workspace_state_key = f"agent_config_workspace_root:{spec.view_id}:{selected_agent_id}"
    knowledge_state_key = f"agent_config_knowledge_root:{spec.view_id}:{selected_agent_id}"
    current_workspace_root = str(_item_value(selected_agent, "workspace_root") or "")
    current_knowledge_root = str(_item_value(selected_agent, "knowledge_root") or "")
    if workspace_state_key not in st.session_state:
        st.session_state[workspace_state_key] = current_workspace_root
    if knowledge_state_key not in st.session_state:
        st.session_state[knowledge_state_key] = current_knowledge_root
    workspace_root = st.text_input(
        "Workspace root",
        key=workspace_state_key,
        help="Workspace roots are typically private to one agent.",
    )
    knowledge_root = st.text_input(
        "Knowledge root",
        key=knowledge_state_key,
        help="Knowledge roots may be shared across agents.",
    )

    workspace_status = _path_status(workspace_root)
    knowledge_status = _path_status(knowledge_root)
    workspace_message = _path_status_message(workspace_root, label="Workspace root")
    knowledge_message = _path_status_message(knowledge_root, label="Knowledge root")
    if str(workspace_root).strip():
        st.caption(f"Workspace root: {workspace_status}")
    if str(knowledge_root).strip():
        st.caption(f"Knowledge root: {knowledge_status}")
    if workspace_message:
        st.warning(workspace_message)
    if knowledge_message:
        st.warning(knowledge_message)

    save_button = st.button(
        save_action.label,
        key=f"agent_config_save:{spec.view_id}:{selected_agent_id}",
        type="primary",
        use_container_width=False,
    )
    if save_button:
        payload = {
            **dict(save_action.payload),
            "agent_id": selected_agent_id,
            "workspace_root": workspace_root,
            "knowledge_root": knowledge_root,
        }
        intent = ModuleViewIntent(
            view_id=spec.view_id,
            intent=save_action.intent,
            action_key=save_action.key,
            scope=save_action.scope,
            item_id=selected_agent_id or None,
            item=selected_agent,
            payload=payload,
        )
        if on_intent is not None:
            on_intent(intent)

    st.divider()
    st.subheader("Current agent configuration")
    render_collection_view(
        CollectionViewDescriptor(
            view_id=spec.view_id,
            title=spec.title,
            description="",
            caption="",
            empty_state=spec.empty_state,
            item_key=spec.item_key,
            columns=spec.columns,
            item_actions=(),
            view_actions=(),
            create_form=None,
            edit_form=None,
            nav_pane=None,
            items=spec.items,
            unsupported_reason=None,
        ),
        on_intent=on_intent,
    )


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


def render_navigation_pane(
    spec: CollectionViewDescriptor,
    *,
    items: list[dict[str, Any]],
    active_item_id: str | None = None,
) -> str | None:
    nav_pane = spec.nav_pane
    if nav_pane is None:
        return None

    st.sidebar.title(nav_pane.title)

    if st.sidebar.button(nav_pane.top_exit_label, key=f"nav-pane-exit-top:{spec.view_id}", use_container_width=True):
        return "__exit__"

    if not items:
        st.sidebar.info(nav_pane.empty_state)
    else:
        for index, item in enumerate(items):
            item_id = str(item.get(nav_pane.item_value_key) or "").strip()
            label = str(item.get(nav_pane.item_label_key) or "").strip() or f"Item {index + 1}"
            subtitle = str(item.get(nav_pane.item_subtitle_key) or "").strip()
            detail = str(item.get(nav_pane.item_detail_key) or "").strip()
            if st.sidebar.button(
                label,
                key=f"nav-pane-item:{spec.view_id}:{item_id or index}",
                type="primary" if active_item_id and item_id == active_item_id else "secondary",
                use_container_width=True,
            ):
                return item_id or None
            if subtitle:
                st.sidebar.caption(subtitle)
            if detail:
                st.sidebar.caption(detail)

    if st.sidebar.button(nav_pane.bottom_exit_label, key=f"nav-pane-exit-bottom:{spec.view_id}", use_container_width=True):
        return "__exit__"

    return None


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
        current_section = ""
        for field in form.fields:
            if field.section and field.section != current_section:
                st.subheader(field.section)
                current_section = field.section
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
        number_kwargs = {
            "min_value": field.min_value,
            "max_value": field.max_value,
            "step": field.step,
        }
        if _uses_float_numbers(number_value, number_kwargs):
            number_value = float(number_value)
            if number_kwargs["min_value"] is not None:
                number_kwargs["min_value"] = float(number_kwargs["min_value"])
            if number_kwargs["max_value"] is not None:
                number_kwargs["max_value"] = float(number_kwargs["max_value"])
            if number_kwargs["step"] is not None:
                number_kwargs["step"] = float(number_kwargs["step"])
        else:
            number_value = int(number_value)
        return st.number_input(
            field.label,
            value=number_value,
            min_value=number_kwargs["min_value"],
            max_value=number_kwargs["max_value"],
            step=number_kwargs["step"],
            **common_kwargs,
        )
    if field_type == "checkbox":
        return st.checkbox(
            field.label,
            value=bool(value),
            help=field.help_text or None,
        )
    if field_type == "color":
        return st.color_picker(
            field.label,
            value=_stringify_form_value(value) or "#000000",
            help=field.help_text or None,
        )
    if field_type == "slider":
        slider_value = value if isinstance(value, (int, float)) else field.default
        return st.slider(
            field.label,
            min_value=field.min_value,
            max_value=field.max_value,
            value=slider_value,
            step=field.step,
            help=field.help_text or None,
        )
    if field_type == "select":
        options = [_normalize_select_option(option) for option in field.options]
        if not options:
            return ""
        default_value = value if value not in (None, "") else field.default
        index = _select_option_index(options, default_value)
        selected = st.selectbox(
            field.label,
            options,
            index=index,
            format_func=lambda option: str(option.get("label") or option.get("value") or ""),
            help=field.help_text or None,
        )
        if isinstance(selected, Mapping):
            return selected.get("value")
        return selected
    if field_type == "date":
        return st.date_input(
            field.label,
            value=_coerce_date(value, field.default),
            help=field.help_text or None,
        )
    if field_type == "time":
        return st.time_input(
            field.label,
            value=_coerce_time(value, field.default),
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


def _uses_float_numbers(number_value: int | float, number_kwargs: dict[str, Any]) -> bool:
    if isinstance(number_value, float):
        return True
    for key in ("min_value", "max_value", "step"):
        if isinstance(number_kwargs.get(key), float):
            return True
    return False


def _normalize_select_option(option: Any) -> dict[str, Any]:
    if isinstance(option, Mapping):
        label = option.get("label") or option.get("name") or option.get("title") or option.get("text")
        value = option.get("value")
        if value in (None, ""):
            value = option.get("id") or option.get("key") or label
        return {
            "label": str(label or value or ""),
            "value": value,
        }
    return {"label": str(option), "value": option}


def _select_option_index(options: list[dict[str, Any]], selected_value: Any) -> int:
    if selected_value in (None, ""):
        return 0
    for index, option in enumerate(options):
        if option.get("value") == selected_value or option.get("label") == str(selected_value):
            return index
    try:
        normalized = int(selected_value)
    except (TypeError, ValueError):
        normalized = None
    if normalized is not None:
        for index, option in enumerate(options):
            if option.get("value") == normalized:
                return index
    return 0


def _selected_selectbox_index(items: list[Any], selected_id: Any, item_key: str) -> int:
    selected_text = str(selected_id or "").strip()
    for index, item in enumerate(items):
        if str(_item_id(item, item_key) or "").strip() == selected_text:
            return index
    return 0


def _path_status(path_value: str) -> str:
    path = str(path_value or "").strip()
    if not path:
        return "Not set"
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return "Relative path"
    if not candidate.exists():
        return "Missing"
    if not candidate.is_dir():
        return "Not a directory"
    if not os.access(candidate, os.R_OK | os.X_OK):
        return "Not readable"
    if not os.access(candidate, os.W_OK | os.X_OK):
        return "Not writable"
    return "Ready"


def _path_status_message(path_value: str, *, label: str) -> str | None:
    path = str(path_value or "").strip()
    if not path:
        return None
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return f"{label} should be an absolute path."
    if not candidate.exists():
        return f"{label} does not exist yet: {path}"
    if not candidate.is_dir():
        return f"{label} is not a directory: {path}"
    if not os.access(candidate, os.R_OK | os.X_OK):
        return f"{label} is not readable by the current process: {path}"
    if not os.access(candidate, os.W_OK | os.X_OK):
        return f"{label} is not writable by the current process: {path}"
    return None


def _coerce_date(value: Any, default: Any) -> date:
    candidate = value if value not in (None, "") else default
    if isinstance(candidate, datetime):
        return candidate.date()
    if isinstance(candidate, date):
        return candidate
    if isinstance(candidate, str) and candidate.strip():
        raw = candidate.strip()
        if raw.endswith("Z"):
            raw = raw[:-1]
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            try:
                return datetime.fromisoformat(raw).date()
            except ValueError:
                pass
    return datetime.now().astimezone().date()


def _coerce_time(value: Any, default: Any) -> time:
    candidate = value if value not in (None, "") else default
    if isinstance(candidate, datetime):
        return candidate.time().replace(microsecond=0)
    if isinstance(candidate, time):
        return candidate.replace(microsecond=0, tzinfo=None)
    if isinstance(candidate, str) and candidate.strip():
        raw = candidate.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            try:
                return time.fromisoformat(raw).replace(microsecond=0, tzinfo=None)
            except ValueError:
                pass
        else:
            return parsed.time().replace(microsecond=0)
    return datetime.now().astimezone().time().replace(microsecond=0)


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
