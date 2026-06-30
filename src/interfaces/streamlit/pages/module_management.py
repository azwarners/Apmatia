"""Module management page for module and view visibility controls."""
from __future__ import annotations

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    list_modules,
    set_module_visibility,
    set_module_view_visibility,
)


def _module_toggle_label(module: dict[str, object]) -> str:
    return "Show module" if bool(module.get("hidden", False)) else "Hide module"


def _view_toggle_label(view: dict[str, object]) -> str:
    return "Show view" if bool(view.get("hidden", False)) else "Hide view"


def render() -> None:
    try:
        modules = list_modules()
    except ApiError as error:
        st.error(f"Unable to load module catalog: {error.detail}")
        return

    st.title("Module Management")
    st.caption("Hide modules or individual module views through the local API. This is the first step toward broader module configuration.")

    if not modules:
        st.info("No modules are registered yet.")
        return

    for module in modules:
        module_id = str(module.get("module_id") or "")
        module_name = str(module.get("name") or module_id or "Unnamed module")
        module_hidden = bool(module.get("hidden", False))
        views = list(module.get("views") or [])

        with st.container(border=True):
            title_col, button_col = st.columns([3, 1])
            with title_col:
                st.write(f"**{module_name}**")
                st.caption(f"{module_id} · version {module.get('version') or 'unknown'}")
            with button_col:
                if st.button(_module_toggle_label(module), key=f"toggle_module_{module_id}", use_container_width=True):
                    try:
                        set_module_visibility(module_id, hidden=not module_hidden)
                    except ApiError as error:
                        st.error(f"Unable to update module visibility: {error.detail}")
                    else:
                        st.success(f"{module_name} {'hidden' if not module_hidden else 'shown'}.")
                        st.rerun()

            description = str(module.get("description") or "").strip()
            if description:
                st.write(description)

            view_count = int(module.get("view_count") or len(views))
            visible_view_count = int(module.get("visible_view_count") or 0)
            module_state = "hidden" if module_hidden else "visible"
            st.caption(f"Module is currently {module_state}. {visible_view_count} of {view_count} views are currently visible.")

            if not views:
                st.info("This module has no registered views yet.")
                continue

            st.subheader("Views")
            for view in views:
                view_id = str(view.get("view_id") or "")
                view_name = str(view.get("name") or view_id or "Unnamed view")
                effective_hidden = bool(view.get("effective_hidden", False))
                explicit_hidden = bool(view.get("hidden", False))

                view_left, view_right = st.columns([3, 1])
                with view_left:
                    st.write(view_name)
                    description = str(view.get("description") or "").strip()
                    state_text = "hidden by module" if module_hidden and not explicit_hidden else ("hidden" if effective_hidden else "visible")
                    st.caption(f"{view_id} · {state_text}")
                    if description:
                        st.caption(description)
                with view_right:
                    if st.button(_view_toggle_label(view), key=f"toggle_view_{view_id}", use_container_width=True):
                        try:
                            set_module_view_visibility(view_id, hidden=not explicit_hidden)
                        except ApiError as error:
                            st.error(f"Unable to update view visibility: {error.detail}")
                        else:
                            st.success(f"{view_name} {'hidden' if not explicit_hidden else 'shown'}.")
                            st.rerun()
