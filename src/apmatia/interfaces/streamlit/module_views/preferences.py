"""Streamlit renderer for module controls exposed by Preferences."""
from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from apmatia.interfaces.streamlit.api_client import ApiError, execute_module_command


COMMAND_PREFIX = "preferences"
PREFERENCES_MODULE_ID = "preferences"
MODULES_VIEW_ID = "preferences.modules.view"


def render_legacy(items: Iterable[dict[str, object]]) -> None:
    catalog = next((item for item in items if isinstance(item, dict)), {})
    modules = [item for item in catalog.get("modules", []) if isinstance(item, dict)]
    show_development_modules = bool(catalog.get("show_development_modules", False))

    st.title("Modules")
    enable_all_modules = st.toggle(
        "Enable all modules",
        value=show_development_modules,
        help=(
            "Off activates only stable, default-enabled modules. On also activates development modules, "
            "including their views, tools, commands, and background services."
        ),
    )
    if enable_all_modules != show_development_modules:
        if _execute("set_activation", enabled=enable_all_modules):
            st.success("All modules enabled." if enable_all_modules else "Stable modules only enabled.")
            st.rerun()
        return

    st.caption(
        "Stable-only mode is the release-safe default. Development modules are not loaded, so their "
        "functionality, views, tools, commands, and background services remain inactive."
    )

    if not modules:
        st.info("No modules are registered yet.")
        return

    for module_index, module in enumerate(modules):
        if _render_module(module, module_index=module_index, module_count=len(modules)):
            return


def _render_module(module: dict[str, object], *, module_index: int, module_count: int) -> bool:
    module_id = str(module.get("module_id") or "").strip()
    module_name = str(module.get("name") or module_id or "Unnamed module")
    module_hidden = bool(module.get("hidden", False))
    views = [item for item in module.get("views", []) if isinstance(item, dict)]
    is_preferences = module_id == PREFERENCES_MODULE_ID

    with st.container(border=True):
        title_col, move_up_col, move_down_col, button_col = st.columns([3, 1, 1, 1])
        with title_col:
            st.subheader(module_name)
            st.caption(f"{module_id} · version {module.get('version') or 'unknown'}")
        with move_up_col:
            if st.button(
                "Move up",
                key=f"move_module_up_{module_id}",
                use_container_width=True,
                disabled=module_index == 0,
            ):
                return _execute_and_rerun(
                    "set_module_order",
                    success=f"{module_name} moved up.",
                    module_id=module_id,
                    new_index=module_index - 1,
                )
        with move_down_col:
            if st.button(
                "Move down",
                key=f"move_module_down_{module_id}",
                use_container_width=True,
                disabled=module_index >= module_count - 1,
            ):
                return _execute_and_rerun(
                    "set_module_order",
                    success=f"{module_name} moved down.",
                    module_id=module_id,
                    new_index=module_index + 1,
                )
        with button_col:
            if st.button(
                "Show module" if module_hidden else "Hide module",
                key=f"toggle_module_{module_id}",
                use_container_width=True,
                disabled=is_preferences,
                help="Preferences stays visible so hidden modules remain recoverable." if is_preferences else None,
            ):
                return _execute_and_rerun(
                    "set_module_visibility",
                    success=f"{module_name} {'shown' if module_hidden else 'hidden'}.",
                    module_id=module_id,
                    hidden=not module_hidden,
                )

        description = str(module.get("description") or "").strip()
        if description:
            st.write(description)

        view_count = int(module.get("view_count") or len(views))
        visible_view_count = int(module.get("visible_view_count") or 0)
        st.caption(
            f"Module is currently {'hidden' if module_hidden else 'visible'}. "
            f"{visible_view_count} of {view_count} views are currently visible."
        )

        if not views:
            st.info("This module has no registered views yet.")
            return False

        st.subheader("Views")
        for view_index, view in enumerate(views):
            if _render_view(
                module_id,
                module_hidden=module_hidden,
                view=view,
                view_index=view_index,
                view_count=len(views),
            ):
                return True
    return False


def _render_view(
    module_id: str,
    *,
    module_hidden: bool,
    view: dict[str, object],
    view_index: int,
    view_count: int,
) -> bool:
    view_id = str(view.get("view_id") or "").strip()
    view_name = str(view.get("name") or view_id or "Unnamed view")
    effective_hidden = bool(view.get("effective_hidden", False))
    explicitly_hidden = bool(view.get("hidden", False))
    is_modules_view = view_id == MODULES_VIEW_ID

    view_left, move_up_col, move_down_col, view_right = st.columns([4, 1, 1, 1])
    with view_left:
        st.write(view_name)
        state_text = "hidden by module" if module_hidden and not explicitly_hidden else ("hidden" if effective_hidden else "visible")
        st.caption(f"{view_id} · {state_text} · order {view_index + 1} of {view_count}")
        description = str(view.get("description") or "").strip()
        if description:
            st.caption(description)
    with move_up_col:
        if st.button(
            "Move up",
            key=f"move_view_up_{view_id}",
            use_container_width=True,
            disabled=view_index == 0,
        ):
            return _execute_and_rerun(
                "set_view_order",
                success=f"{view_name} moved up.",
                module_id=module_id,
                view_id=view_id,
                new_index=view_index - 1,
            )
    with move_down_col:
        if st.button(
            "Move down",
            key=f"move_view_down_{view_id}",
            use_container_width=True,
            disabled=view_index >= view_count - 1,
        ):
            return _execute_and_rerun(
                "set_view_order",
                success=f"{view_name} moved down.",
                module_id=module_id,
                view_id=view_id,
                new_index=view_index + 1,
            )
    with view_right:
        if st.button(
            "Show view" if explicitly_hidden else "Hide view",
            key=f"toggle_view_{view_id}",
            use_container_width=True,
            disabled=is_modules_view,
            help="The Modules view stays visible so hidden views remain recoverable." if is_modules_view else None,
        ):
            return _execute_and_rerun(
                "set_view_visibility",
                success=f"{view_name} {'shown' if explicitly_hidden else 'hidden'}.",
                view_id=view_id,
                hidden=not explicitly_hidden,
            )
    return False


def _execute_and_rerun(verb: str, *, success: str, **payload: object) -> bool:
    if not _execute(verb, **payload):
        return True
    st.success(success)
    st.rerun()
    return True


def _execute(verb: str, **payload: object) -> bool:
    try:
        execute_module_command(f"{COMMAND_PREFIX}.{verb}", **payload)
    except ApiError as error:
        st.error(f"Unable to update module configuration: {error.detail}")
        return False
    return True


render = render_legacy
