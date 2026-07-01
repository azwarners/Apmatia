"""Generic module view page for rendering registry-backed module views."""
from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    execute_module_command,
    list_module_view_items,
    list_modules,
)
from src.interfaces.streamlit.module_views.adapter import adapt_module_view
from src.interfaces.streamlit.module_views.renderers import (
    render_module_view,
    render_module_view_form,
)


def _selected_module_view() -> tuple[dict[str, object] | None, dict[str, object] | None]:
    selected_module_id = str(st.session_state.get("selected_module_id") or "").strip()
    selected_view_id = str(st.session_state.get("selected_module_view_id") or "").strip()
    if not selected_module_id:
        return None, None

    try:
        modules = list_modules()
    except ApiError as error:
        st.error(f"Unable to load modules: {error.detail}")
        return None, None

    selected_module = next(
        (
            module
            for module in modules
            if str(module.get("module_id") or "") == selected_module_id
            and not bool(module.get("hidden", False))
        ),
        None,
    )
    if selected_module is None:
        return None, None

    visible_views = [
        view
        for view in list(selected_module.get("views") or [])
        if not bool(view.get("effective_hidden", False))
    ]
    selected_view = next(
        (view for view in visible_views if str(view.get("view_id") or "") == selected_view_id),
        None,
    )
    if selected_view is None and visible_views:
        selected_view = visible_views[0]
    return selected_module, selected_view


def render() -> None:
    selected_module, selected_view = _selected_module_view()
    if selected_module is None:
        st.title("Module Views")
        st.caption("Render registry-defined module views through the Streamlit adapter.")
        st.info("Select a visible module from the left navigation to open its views.")
        return

    if selected_view is None:
        st.title(str(selected_module.get("name") or "Module"))
        st.caption(str(selected_module.get("module_id") or ""))
        st.info("This module does not currently expose any visible views.")
        return

    view_id = str(selected_view.get("view_id") or "").strip()
    if not view_id:
        st.error("This module view is missing a view ID.")
        return

    try:
        items = list_module_view_items(view_id)
    except ApiError as error:
        st.error(f"Unable to load module view items: {error.detail}")
        items = []

    spec = adapt_module_view(selected_view, items=items)
    intents = render_module_view(spec)
    action_by_key = {action.key: action for action in (*spec.view_actions, *spec.item_actions)}

    create_action = next((action for action in spec.view_actions if action.intent == "create"), None)
    create_open_key = f"module_view_create_open:{spec.view_id}"
    edit_action = next((action for action in spec.item_actions if action.intent == "edit"), None)
    edit_target = _edit_confirmation_target()
    if any(intent.intent == "create" for intent in intents):
        st.session_state[create_open_key] = True

    delete_target = _delete_confirmation_target()
    if delete_target is not None and delete_target.get("view_id") != spec.view_id:
        st.session_state.pop("module_view_delete_target", None)
        delete_target = None
    if delete_target is not None and _delete_target_missing(delete_target, items):
        st.session_state.pop("module_view_delete_target", None)
        delete_target = None

    if edit_target is not None and edit_target.get("view_id") != spec.view_id:
        st.session_state.pop("module_view_edit_target", None)
        edit_target = None
    if edit_target is not None and _edit_target_missing(edit_target, items):
        st.session_state.pop("module_view_edit_target", None)
        edit_target = None

    for intent in intents:
        if intent.intent == "edit":
            command_id = str(intent.payload.get("command_id") or "").strip()
            if not command_id or intent.item_id is None:
                st.warning("Edit is not configured for this item.")
                continue
            if edit_action is None:
                st.warning("Edit is not configured for this module view.")
                continue
            st.session_state["module_view_edit_target"] = {
                "view_id": spec.view_id,
                "item_id": intent.item_id,
                "item_label": _item_label(intent.item),
                "command_id": command_id,
                "item": intent.item,
            }
            st.rerun()
            return
        if intent.intent != "delete":
            continue
        command_id = str(intent.payload.get("command_id") or "").strip()
        if not command_id or intent.item_id is None:
            st.warning("Delete is not configured for this item.")
            continue
        action = action_by_key.get(intent.action_key)
        if action is not None and action.confirmation:
            st.session_state["module_view_delete_target"] = {
                "view_id": spec.view_id,
                "item_id": intent.item_id,
                "item_label": _item_label(intent.item),
                "command_id": command_id,
            }
            st.rerun()
            return
        try:
            execute_module_command(command_id, item_id=intent.item_id)
        except ApiError as error:
            st.error(f"Unable to delete item: {error.detail}")
        else:
            st.success("Item deleted.")
            st.rerun()
            return

    if edit_target is not None:
        command_id = str(edit_target.get("command_id") or "").strip()
        item_id = edit_target.get("item_id")
        if not command_id or item_id is None:
            st.session_state.pop("module_view_edit_target", None)
            st.rerun()
            return

        item_label = str(edit_target.get("item_label") or f"item {item_id}")
        edit_form = spec.edit_form or spec.create_form
        if edit_form is None:
            st.info("Edit is not available for this module view yet.")
            return

        submitted, cancelled, payload = render_module_view_form(
            edit_form,
            form_key=f"module_view_form:{spec.view_id}:{edit_form.key}:edit:{item_id}",
            title=f"Edit {item_label}",
            submit_label="Save changes",
            initial_values=edit_target.get("item") if isinstance(edit_target.get("item"), dict) else None,
        )
        if cancelled:
            st.session_state.pop("module_view_edit_target", None)
            st.rerun()
            return
        if submitted:
            try:
                execute_module_command(command_id, item_id=item_id, **payload)
            except ApiError as error:
                st.error(f"Unable to edit item: {error.detail}")
            else:
                st.session_state.pop("module_view_edit_target", None)
                st.success("Item updated.")
                st.rerun()
                return

    if delete_target is not None:
        command_id = str(delete_target.get("command_id") or "").strip()
        item_id = delete_target.get("item_id")
        if not command_id or item_id is None:
            st.session_state.pop("module_view_delete_target", None)
            st.rerun()
            return

        item_label = str(delete_target.get("item_label") or f"item {item_id}")
        st.warning(f"Delete {item_label}?")
        cancel_col, delete_col, _ = st.columns([1, 1, 8])
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"cancel_delete_module_view:{spec.view_id}:{item_id}",
                width="content",
            ):
                st.session_state.pop("module_view_delete_target", None)
                st.rerun()
        with delete_col:
            if st.button(
                "Delete",
                key=f"confirm_delete_module_view:{spec.view_id}:{item_id}",
                width="content",
                type="primary",
            ):
                try:
                    execute_module_command(command_id, item_id=item_id)
                except ApiError as error:
                    st.error(f"Unable to delete item: {error.detail}")
                else:
                    st.session_state.pop("module_view_delete_target", None)
                    st.success("Item deleted.")
                    st.rerun()
                return

    if st.session_state.get(create_open_key):
        if create_action is None or spec.create_form is None:
            st.info("Create is not available for this module view yet.")
            return

        submitted, cancelled, payload = render_module_view_form(
            spec.create_form,
            form_key=f"module_view_form:{spec.view_id}:{spec.create_form.key}",
        )
        if cancelled:
            st.session_state[create_open_key] = False
            st.rerun()
            return
        if submitted:
            command_id = str(create_action.payload.get("command_id") or "").strip()
            if not command_id:
                st.error("Create is not configured for this module view.")
                return
            try:
                execute_module_command(command_id, **payload)
            except ApiError as error:
                st.error(f"Unable to create item: {error.detail}")
            else:
                st.session_state[create_open_key] = False
                st.success("Item created.")
                st.rerun()


def _delete_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("module_view_delete_target")
    return target if isinstance(target, dict) else None


def _edit_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("module_view_edit_target")
    return target if isinstance(target, dict) else None


def _delete_target_missing(target: dict[str, object], items: Iterable[object]) -> bool:
    try:
        item_id = int(target.get("item_id"))
    except (TypeError, ValueError):
        return True
    return not any(_item_id(item) == item_id for item in items)


def _edit_target_missing(target: dict[str, object], items: Iterable[object]) -> bool:
    return _delete_target_missing(target, items)


def _item_label(item: object | None) -> str:
    if item is None:
        return "item"
    if isinstance(item, dict):
        for key in ("title", "name", "label", "summary", "description"):
            value = item.get(key)
            if value not in (None, ""):
                return str(value)
        return str(item.get("id") or "item")
    for key in ("title", "name", "label", "summary", "description"):
        value = getattr(item, key, None)
        if value not in (None, ""):
            return str(value)
    return str(getattr(item, "id", "item"))


def _item_id(item: object) -> int | str | None:
    if isinstance(item, dict):
        return item.get("id")
    return getattr(item, "id", None)
