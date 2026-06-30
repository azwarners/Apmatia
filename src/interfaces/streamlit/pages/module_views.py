"""Generic module view page for rendering registry-backed module views."""
from __future__ import annotations

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

    create_action = next((action for action in spec.view_actions if action.intent == "create"), None)
    create_open_key = f"module_view_create_open:{spec.view_id}"
    if any(intent.intent == "create" for intent in intents):
        st.session_state[create_open_key] = True

    for intent in intents:
        if intent.intent == "edit":
            st.info("Edit flows are not wired up for this module view yet.")
            continue
        if intent.intent != "delete":
            continue
        command_id = str(intent.payload.get("command_id") or "").strip()
        if not command_id or intent.item_id is None:
            st.warning("Delete is not configured for this item.")
            continue
        try:
            execute_module_command(command_id, item_id=intent.item_id)
        except ApiError as error:
            st.error(f"Unable to delete item: {error.detail}")
        else:
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
