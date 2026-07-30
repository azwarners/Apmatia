"""Controller for generic module views rendered from serialized view documents."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    execute_module_command,
    list_agents,
    list_llm_configs,
    list_module_view_items,
    load_view_source,
)
from apmatia.interfaces.streamlit.module_views.contract_renderer import (
    apply_effects,
    find_form_component,
    initialize_view_state,
    render_form_component,
    render_view_document,
)


def is_contract_ready_view(view: Mapping[str, Any]) -> bool:
    """Return whether a catalog view has completed portable generic migration."""
    metadata = view.get("metadata")
    return bool(metadata.get("view_contract_ready", False)) if isinstance(metadata, Mapping) else False


def render_portable_module_view(document: Mapping[str, Any]) -> None:
    """Load declared sources, render a generic document, and execute its CRUD intents."""
    view_id = str(document.get("view_id") or "").strip()
    if not view_id:
        st.error("This portable view document is missing a view ID.")
        return

    state = initialize_view_state(document)
    sources = _load_data_sources(document, state=state)
    items = sources.get("items")
    item_list = list(items) if isinstance(items, (list, tuple)) else []
    actions = {
        str(action.get("key") or ""): action
        for action in _mapping_sequence(document.get("actions"))
        if str(action.get("key") or "")
    }
    intents = render_view_document(document, data_sources=sources)

    create_key = f"contract-create-open:{view_id}"
    edit_key = f"contract-edit-target:{view_id}"
    delete_key = f"contract-delete-target:{view_id}"
    for intent in intents:
        action = actions.get(str(intent.get("action_key") or ""), {})
        intent_name = str(intent.get("intent") or "")
        if intent_name == "create":
            st.session_state[create_key] = True
        elif intent_name == "edit":
            st.session_state[edit_key] = {
                "item_id": intent.get("item_id"),
                "item": intent.get("item"),
                "action_key": intent.get("action_key"),
            }
        elif bool(action.get("confirmation", False)):
            st.session_state[delete_key] = {
                "item_id": intent.get("item_id"),
                "item": intent.get("item"),
                "action_key": intent.get("action_key"),
            }
        else:
            _execute_intent(document, action, intent)
            return

    edit_target = st.session_state.get(edit_key)
    if isinstance(edit_target, Mapping):
        _render_edit_flow(document, actions, edit_target, data_sources=sources, state_key=edit_key)

    delete_target = st.session_state.get(delete_key)
    if isinstance(delete_target, Mapping):
        if _target_missing(delete_target, item_list, _item_key(document)):
            st.session_state.pop(delete_key, None)
        else:
            _render_confirmation_flow(document, actions, delete_target, state_key=delete_key)

    if bool(st.session_state.get(create_key)):
        _render_create_flow(document, actions, data_sources=sources, state_key=create_key)


def _load_data_sources(document: Mapping[str, Any], *, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for source in _mapping_sequence(document.get("data_sources")):
        key = str(source.get("key") or "")
        operation = str(source.get("operation") or "")
        if not key:
            continue
        if operation.startswith("module_view_items:"):
            view_id = operation.removeprefix("module_view_items:").strip()
            try:
                sources[key] = list_module_view_items(view_id)
            except ApiError as error:
                st.error(str(source.get("error_text") or f"Unable to load module view items: {error.detail}"))
                sources[key] = []
        elif operation in {"agents:list", "model_configs:list", "list_agents", "list_llm_configs"}:
            loader = list_agents if operation in {"agents:list", "list_agents"} else list_llm_configs
            try:
                sources[key] = _project_options(loader(), source.get("parameters"))
            except ApiError as error:
                st.error(str(source.get("error_text") or f"Unable to load {key}: {error.detail}"))
                sources[key] = []
        elif operation in {
            "discussion_tree",
            "discussion_state",
            "discussion_activity",
            "list_contacts",
            "list_tasks",
            "get_current_task",
            "list_workspace_files",
            "list_knowledge_files",
            "list_agents",
            "list_llm_configs",
        }:
            try:
                parameters = {
                    key: _resolve_source_parameter(value, state or {})
                    for key, value in dict(source.get("parameters") or {}).items()
                }
                if operation in {"discussion_state", "discussion_activity", "get_current_task"}:
                    parameter_key = "discussion_id" if operation.startswith("discussion_") else "task_id"
                    parameters.setdefault(
                        parameter_key,
                        (state or {}).get("selected_discussion_id" if parameter_key == "discussion_id" else "selected_task_id"),
                    )
                sources[key] = load_view_source(operation, **parameters)
            except ApiError as error:
                st.error(str(source.get("error_text") or f"Unable to load {key}: {error.detail}"))
                sources[key] = [] if str(source.get("kind") or "collection") in {"collection", "stream", "tree"} else {}
        else:
            st.warning(f"Unsupported portable data-source operation: {operation}")
            sources[key] = [] if str(source.get("kind") or "collection") == "collection" else None
    return sources


def _resolve_source_parameter(value: Any, state: Mapping[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$state."):
        return state.get(value.removeprefix("$state."))
    return value


def _render_create_flow(
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    *,
    data_sources: Mapping[str, Any],
    state_key: str,
) -> None:
    component = find_form_component(document, "create")
    action = next((item for item in actions.values() if str(item.get("intent") or "") == "create"), None)
    if component is None or action is None:
        st.warning("Create is not fully described by this view document.")
        st.session_state.pop(state_key, None)
        return
    draft_key = f"{state_key}:draft"
    result_key = f"{state_key}:result"
    initial_values = st.session_state.get(draft_key)
    if not isinstance(initial_values, Mapping):
        initial_values = None
    result = st.session_state.get(result_key)
    if isinstance(result, Mapping):
        _render_form_action_result(result)
    submitted, cancelled, payload, selected_action = render_form_component(
        component,
        view_id=str(document.get("view_id") or ""),
        form_key_suffix="create",
        initial_values=initial_values,
        data_sources=data_sources,
    )
    if cancelled:
        st.session_state.pop(state_key, None)
        st.session_state.pop(draft_key, None)
        st.session_state.pop(result_key, None)
        st.rerun()
        return
    if selected_action:
        action = actions.get(selected_action)
        if action is None:
            st.warning(f"Unknown form action: {selected_action}")
            return
        action_result = _execute_form_action(action, payload)
        if action_result is not None:
            draft = dict(payload)
            item = action_result.get("item")
            if isinstance(item, Mapping):
                draft.update(item)
            field_keys = {
                str((field.get("properties") or {}).get("key") or "")
                for field in _mapping_sequence(component.get("children"))
            }
            draft.update({key: value for key, value in action_result.items() if key in field_keys})
            st.session_state[draft_key] = draft
            st.session_state[result_key] = dict(action_result)
            st.rerun()
        return
    if submitted:
        intent = _intent_for_action(document, action, payload=payload)
        if _execute_intent(document, action, intent):
            st.session_state.pop(state_key, None)
            st.session_state.pop(draft_key, None)
            st.session_state.pop(result_key, None)


def _execute_form_action(action: Mapping[str, Any], payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    command_id = str(action.get("command_id") or "").strip()
    if not command_id:
        st.warning(f"{str(action.get('label') or 'Action')} is not connected to a module command.")
        return None
    try:
        result = execute_module_command(command_id, **_json_safe_payload(payload))
    except ApiError as error:
        st.error(error.detail)
        return None
    return result if isinstance(result, Mapping) else {"message": str(result or "Action completed.")}


def _render_form_action_result(result: Mapping[str, Any]) -> None:
    message = str(result.get("message") or "").strip()
    if message:
        st.success(message)
    for key, value in result.items():
        text = str(value or "").strip()
        if not text or key == "message":
            continue
        label = key.replace("_", " ").title()
        if key.endswith("_error"):
            st.warning(text)
        elif key.endswith("_command"):
            st.caption(label)
            st.code(text, language="bash")


def _render_edit_flow(
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    data_sources: Mapping[str, Any],
    state_key: str,
) -> None:
    component = find_form_component(document, "edit") or find_form_component(document, "create")
    action = actions.get(str(target.get("action_key") or "")) or next(
        (item for item in actions.values() if str(item.get("intent") or "") == "edit"),
        None,
    )
    if component is None or action is None:
        st.warning("Edit is not fully described by this view document.")
        st.session_state.pop(state_key, None)
        return
    item_id = target.get("item_id")
    item = target.get("item") if isinstance(target.get("item"), Mapping) else {}
    submitted, cancelled, payload, selected_action = render_form_component(
        component,
        view_id=str(document.get("view_id") or ""),
        form_key_suffix=f"edit:{item_id}",
        initial_values=item,
        title=f"Edit {_item_label(item, item_id)}",
        submit_label="Save changes",
        data_sources=data_sources,
    )
    if cancelled:
        st.session_state.pop(state_key, None)
        st.rerun()
        return
    if selected_action:
        st.warning(f"Unsupported generic form action: {selected_action}")
    if submitted:
        intent = _intent_for_action(document, action, item=item, item_id=item_id, payload=payload)
        if _execute_intent(document, action, intent):
            st.session_state.pop(state_key, None)


def _render_confirmation_flow(
    document: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    state_key: str,
) -> None:
    action = actions.get(str(target.get("action_key") or ""))
    if action is None:
        st.session_state.pop(state_key, None)
        return
    item_id = target.get("item_id")
    item = target.get("item")
    label = _item_label(item, item_id)
    st.warning(f"{str(action.get('label') or 'Confirm')} {label}?")
    cancel_column, confirm_column, _ = st.columns([1, 1, 8])
    with cancel_column:
        if st.button("Cancel", key=f"contract-confirm-cancel:{document.get('view_id')}:{item_id}"):
            st.session_state.pop(state_key, None)
            st.rerun()
    with confirm_column:
        if st.button(
            str(action.get("label") or "Confirm"),
            key=f"contract-confirm:{document.get('view_id')}:{item_id}:{action.get('key')}",
            type="primary",
        ):
            intent = _intent_for_action(document, action, item=item, item_id=item_id)
            if _execute_intent(document, action, intent):
                st.session_state.pop(state_key, None)


def _execute_intent(
    document: Mapping[str, Any],
    action: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> bool:
    state = initialize_view_state(document)
    payload = _resolve_payload(dict(intent.get("payload") or {}), state=state, item=intent.get("item"))
    command_id = str(payload.pop("command_id", "") or action.get("command_id") or "").strip()
    payload.pop("operation", None)
    item_id = intent.get("item_id")
    if item_id is not None:
        payload.setdefault("item_id", item_id)
    item = intent.get("item")
    if isinstance(item, Mapping):
        payload.setdefault("item", dict(item))
    if not command_id:
        st.warning(f"{str(action.get('label') or 'Action')} is not connected to a module command.")
        return False
    try:
        result = execute_module_command(command_id, **_json_safe_payload(payload))
    except ApiError as error:
        st.error(error.detail)
        apply_effects(document, _mapping_sequence(action.get("failure_effects")), result={"error": error.detail})
        return False

    refresh = apply_effects(document, _mapping_sequence(action.get("success_effects")), result=result)
    message = str(result.get("message") or "") if isinstance(result, Mapping) else ""
    if isinstance(result, Mapping):
        warning = str(result.get("warning") or "").strip()
        if warning:
            st.warning(warning)
        warnings = result.get("warnings")
        if isinstance(warnings, list):
            for entry in warnings:
                text = str(entry or "").strip()
                if text:
                    st.warning(text)
    st.success(message or f"{str(action.get('label') or 'Action')} completed.")
    if refresh:
        st.rerun()
    return True


def _resolve_payload(value: Any, *, state: Mapping[str, Any], item: Any = None) -> Any:
    if isinstance(value, str):
        if value.startswith("$state."):
            return _value_at_path(state, value.removeprefix("$state."))
        if value.startswith("$item."):
            return _value_at_path(item, value.removeprefix("$item."))
        return value
    if isinstance(value, Mapping):
        return {str(key): _resolve_payload(item_value, state=state, item=item) for key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_resolve_payload(item_value, state=state, item=item) for item_value in value]
    return value


def _value_at_path(value: Any, path: str) -> Any:
    current = value
    for part in [piece for piece in path.split(".") if piece]:
        if isinstance(current, Mapping):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            break
    return current


def _intent_for_action(
    document: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    item: Any = None,
    item_id: Any = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(action.get("payload") or {})
    merged.update(dict(payload or {}))
    command_id = str(action.get("command_id") or "")
    if command_id:
        merged["command_id"] = command_id
    return {
        "view_id": str(document.get("view_id") or ""),
        "intent": str(action.get("intent") or ""),
        "action_key": str(action.get("key") or ""),
        "scope": str(action.get("scope") or "view"),
        "item_id": item_id,
        "item": item,
        "payload": merged,
    }


def _item_key(document: Mapping[str, Any]) -> str:
    for source in _mapping_sequence(document.get("data_sources")):
        if str(source.get("kind") or "") == "collection":
            return str(source.get("item_key") or "id")
    return "id"


def _target_missing(target: Mapping[str, Any], items: list[Any], item_key: str) -> bool:
    target_id = str(target.get("item_id") or "")
    return bool(target_id) and all(str(_item_value(item, item_key) or "") != target_id for item in items)


def _item_label(item: Any, item_id: Any) -> str:
    for key in ("name", "title", "label", "user_alias", "path"):
        value = _item_value(item, key)
        if value not in (None, ""):
            return str(value)
    return f"item {item_id}"


def _item_value(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in list(value or []) if isinstance(item, Mapping)]


def _project_options(items: Any, parameters: Any) -> list[dict[str, Any]]:
    config = parameters if isinstance(parameters, Mapping) else {}
    raw_label_keys = config.get("label_keys") or (config.get("label_key") or "label",)
    label_keys = [str(key) for key in raw_label_keys] if isinstance(raw_label_keys, (list, tuple)) else [str(raw_label_keys)]
    value_key = str(config.get("value_key") or "id")
    default_label = str(config.get("default_label") or "Unnamed item")
    options: list[dict[str, Any]] = []
    if bool(config.get("include_empty", False)):
        options.append({"label": str(config.get("empty_label") or "None"), "value": None})
    for item in list(items or []):
        if not isinstance(item, Mapping) or item.get(value_key) is None:
            continue
        label = next((str(item.get(key)).strip() for key in label_keys if str(item.get(key) or "").strip()), default_label)
        options.append({"label": label, "value": item.get(value_key)})
    return options


def _json_safe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (datetime, date, time)):
            result[key] = value.isoformat()
        elif hasattr(value, "getvalue"):
            result[key] = value.getvalue()
        else:
            result[key] = value
    return result
