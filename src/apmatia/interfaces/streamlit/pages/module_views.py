"""Generic module view page for rendering registry-backed module views."""
from __future__ import annotations

from dataclasses import replace
from collections.abc import Iterable

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_discussion,
    create_group,
    discussion_tree,
    execute_module_command,
    list_agents,
    list_groups,
    list_llm_configs,
    list_module_view_items,
    list_modules,
    list_tool_definitions,
    open_discussion,
)
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.renderers import (
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
    spec = _enrich_participant_view(spec, selected_view)
    is_participant_view = _is_participant_view(selected_view)
    render_spec = replace(spec, create_form=None, view_actions=()) if is_participant_view else spec
    intents = render_module_view(render_spec)
    action_by_key = {action.key: action for action in (*spec.view_actions, *spec.item_actions)}

    create_action = next((action for action in spec.view_actions if action.intent == "create"), None)
    edit_action = next((action for action in spec.item_actions if action.intent == "edit"), None)
    disable_action = next((action for action in spec.item_actions if action.intent == "disable"), None)
    edit_target = _edit_confirmation_target()

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

    disable_target = _disable_confirmation_target()
    if disable_target is not None and disable_target.get("view_id") != spec.view_id:
        st.session_state.pop("module_view_disable_target", None)
        disable_target = None
    if disable_target is not None and _disable_target_missing(disable_target, items):
        st.session_state.pop("module_view_disable_target", None)
        disable_target = None

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
        if intent.intent == "disable":
            command_id = str(intent.payload.get("command_id") or "").strip()
            if not command_id or intent.item_id is None:
                st.warning("Disable is not configured for this item.")
                continue
            if disable_action is None:
                st.warning("Disable is not configured for this module view.")
                continue
            st.session_state["module_view_disable_target"] = {
                "view_id": spec.view_id,
                "item_id": intent.item_id,
                "item_label": _item_label(intent.item),
                "command_id": command_id,
                "item": intent.item,
            }
            st.rerun()
            return
        if intent.intent == "inspect_resources":
            command_id = str(intent.payload.get("command_id") or "").strip()
            if not command_id:
                st.warning("Resource inspection is not configured for this module view.")
                continue
            try:
                result = execute_module_command(command_id)
            except ApiError as error:
                st.error(f"Unable to inspect resources: {error.detail}")
            else:
                st.session_state["module_view_resource_snapshot"] = {
                    "view_id": spec.view_id,
                    "result": result,
                }
                st.success("Local resources inspected.")
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
        if is_participant_view:
            initial_values = edit_target.get("item") if isinstance(edit_target.get("item"), dict) else None
            try:
                agents = list_agents()
            except ApiError as error:
                st.error(f"Unable to load agents: {error.detail}")
                agents = []
            try:
                groups = list_groups()
            except ApiError as error:
                st.error(f"Unable to load groups: {error.detail}")
                groups = []
            try:
                model_configs = list_llm_configs()
            except ApiError as error:
                st.error(f"Unable to load model configs: {error.detail}")
                model_configs = []
            default_target_kind = "group" if isinstance(initial_values, dict) and initial_values.get("group_id") not in (None, "") else "agent"
            target_kind = st.radio(
                "Target type",
                options=("agent", "group"),
                horizontal=True,
                index=0 if default_target_kind == "agent" else 1,
                key=f"participant_target_kind_edit:{spec.view_id}:{item_id}",
            )
            rendered_form = _render_participant_target_form(
                view_id=spec.view_id,
                title=f"Edit {item_label}",
                submit_label="Save changes",
                target_kind=target_kind,
                agents=agents,
                groups=groups,
                model_configs=model_configs,
                initial_values=initial_values,
                form_key=f"participant_edit_form:{spec.view_id}:{item_id}",
            )
            if rendered_form is None:
                st.info("Edit is not available for this module view yet.")
                return

            submitted, cancelled, payload = rendered_form
            if cancelled:
                st.session_state.pop("module_view_edit_target", None)
                st.rerun()
                return
            if submitted:
                try:
                    result = execute_module_command(command_id, item_id=item_id, **payload)
                except ApiError as error:
                    st.error(f"Unable to edit item: {error.detail}")
                else:
                    st.session_state.pop("module_view_edit_target", None)
                    if isinstance(result, dict):
                        bootstrap_message = str(result.get("message") or "").strip()
                        if bootstrap_message:
                            st.success(bootstrap_message)
                        elif bool(result.get("bootstrap_attempted")) and bool(result.get("bootstrap_succeeded")):
                            st.success("Item updated and SSH key installed.")
                        elif bool(result.get("bootstrap_attempted")) and str(result.get("bootstrap_error") or "").strip():
                            st.warning(str(result.get("bootstrap_error") or ""))
                            st.success("Item updated.")
                        else:
                            st.success("Item updated.")
                    else:
                        st.success("Item updated.")
                    st.rerun()
                    return
        else:
            edit_form = spec.edit_form or spec.create_form
            if edit_form is None:
                st.info("Edit is not available for this module view yet.")
                return

            rendered_form = render_module_view_form(
                edit_form,
                form_key=f"module_view_form:{spec.view_id}:{edit_form.key}:edit:{item_id}",
                title=f"Edit {item_label}",
                submit_label="Save changes",
                initial_values=edit_target.get("item") if isinstance(edit_target.get("item"), dict) else None,
            )
            if len(rendered_form) == 4:
                submitted, cancelled, payload, _action_key = rendered_form
            else:
                submitted, cancelled, payload = rendered_form
            if cancelled:
                st.session_state.pop("module_view_edit_target", None)
                st.rerun()
                return
            if submitted:
                try:
                    result = execute_module_command(command_id, item_id=item_id, **payload)
                except ApiError as error:
                    st.error(f"Unable to edit item: {error.detail}")
                else:
                    st.session_state.pop("module_view_edit_target", None)
                    if isinstance(result, dict):
                        bootstrap_message = str(result.get("message") or "").strip()
                        if bootstrap_message:
                            st.success(bootstrap_message)
                        elif bool(result.get("bootstrap_attempted")) and bool(result.get("bootstrap_succeeded")):
                            st.success("Item updated and SSH key installed.")
                        elif bool(result.get("bootstrap_attempted")) and str(result.get("bootstrap_error") or "").strip():
                            st.warning(str(result.get("bootstrap_error") or ""))
                            st.success("Item updated.")
                        else:
                            st.success("Item updated.")
                    else:
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

    if disable_target is not None:
        command_id = str(disable_target.get("command_id") or "").strip()
        item_id = disable_target.get("item_id")
        if not command_id or item_id is None:
            st.session_state.pop("module_view_disable_target", None)
            st.rerun()
            return

        item_label = str(disable_target.get("item_label") or f"item {item_id}")
        st.warning(f"Disable {item_label}?")
        cancel_col, disable_col, _ = st.columns([1, 1, 8])
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"cancel_disable_module_view:{spec.view_id}:{item_id}",
                width="content",
            ):
                st.session_state.pop("module_view_disable_target", None)
                st.rerun()
        with disable_col:
            if st.button(
                "Disable",
                key=f"confirm_disable_module_view:{spec.view_id}:{item_id}",
                width="content",
                type="primary",
            ):
                try:
                    execute_module_command(command_id, item_id=item_id)
                except ApiError as error:
                    st.error(f"Unable to disable item: {error.detail}")
                else:
                    st.session_state.pop("module_view_disable_target", None)
                    st.success("Item disabled.")
                    st.rerun()
                return

    resource_snapshot = st.session_state.get("module_view_resource_snapshot")
    if isinstance(resource_snapshot, dict) and resource_snapshot.get("view_id") == spec.view_id:
        st.divider()
        st.subheader("Local resources")
        result = resource_snapshot.get("result")
        if isinstance(result, dict):
            st.json(result)
        else:
            st.write(result)

    if is_participant_view:
        _render_participant_view_controls(spec=spec, selected_view=selected_view, create_action=create_action, edit_target=edit_target)
        return

    create_open_key = f"module_view_create_open:{spec.view_id}"
    create_draft_key = f"module_view_create_draft:{spec.view_id}"
    create_notice_key = f"module_view_create_notice:{spec.view_id}"
    form_action_by_key = {action.key: action for action in (spec.create_form.actions if spec.create_form else ())}
    if any(intent.intent == "create" for intent in intents):
        st.session_state[create_open_key] = True

    create_notice = st.session_state.get(create_notice_key)
    if isinstance(create_notice, dict) and create_notice.get("message"):
        st.success(str(create_notice.get("message") or ""))
        install_command = str(create_notice.get("install_command") or "").strip()
        if install_command:
            st.caption("Copy and run this on the host running Apmatia after the key has been prepared.")
            st.code(install_command, language="bash")
        bootstrap_error = str(create_notice.get("bootstrap_error") or "").strip()
        if bootstrap_error:
            st.warning(bootstrap_error)

    if st.session_state.get(create_open_key):
        if create_action is None or spec.create_form is None:
            st.info("Create is not available for this module view yet.")
            return

        initial_values = st.session_state.get(create_draft_key)
        if not isinstance(initial_values, dict):
            initial_values = None
        rendered_form = render_module_view_form(
            spec.create_form,
            form_key=f"module_view_form:{spec.view_id}:{spec.create_form.key}",
            initial_values=initial_values,
        )
        if len(rendered_form) == 4:
            submitted, cancelled, payload, action_key = rendered_form
        else:
            submitted, cancelled, payload = rendered_form
            action_key = None
        if cancelled:
            st.session_state[create_open_key] = False
            st.session_state.pop(create_draft_key, None)
            st.session_state.pop(create_notice_key, None)
            st.rerun()
            return
        create_action_result = form_action_by_key.get(action_key or "")
        if action_key and create_action_result is not None:
            command_id = str(create_action_result.payload.get("command_id") or "").strip()
            if not command_id:
                st.error("This form action is not configured.")
                return
            try:
                result = execute_module_command(command_id, **payload)
            except ApiError as error:
                st.error(f"Unable to prepare SSH key: {error.detail}")
            else:
                if isinstance(result, dict):
                    draft_values = dict(payload)
                    credential_ref = str(result.get("credential_ref") or result.get("private_key_path") or "").strip()
                    if credential_ref:
                        draft_values["credential_ref"] = credential_ref
                    st.session_state[create_draft_key] = draft_values
                    st.session_state[create_notice_key] = {
                        "message": str(result.get("message") or "SSH key prepared."),
                        "install_command": str(result.get("ssh_public_key_install_command") or "").strip(),
                        "bootstrap_error": str(result.get("bootstrap_error") or "").strip(),
                    }
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
                st.session_state.pop(create_draft_key, None)
                st.session_state.pop(create_notice_key, None)
                st.success("Item created.")
                st.rerun()


def _delete_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("module_view_delete_target")
    return target if isinstance(target, dict) else None


def _edit_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("module_view_edit_target")
    return target if isinstance(target, dict) else None


def _disable_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("module_view_disable_target")
    return target if isinstance(target, dict) else None


def _delete_target_missing(target: dict[str, object], items: Iterable[object]) -> bool:
    try:
        item_id = int(target.get("item_id"))
    except (TypeError, ValueError):
        return True
    return not any(_item_id(item) == item_id for item in items)


def _enrich_participant_view(
    spec: object,
    selected_view: dict[str, object],
):
    view_id = str(selected_view.get("view_id") or "").strip()
    if not view_id.endswith("participants.view"):
        return spec

    create_form = getattr(spec, "create_form", None)
    if create_form is None:
        return spec

    try:
        agents = list_agents()
    except ApiError:
        agents = []
    try:
        groups = list_groups()
    except ApiError:
        groups = []

    target_options: list[str] = []
    for agent in agents:
        agent_id = agent.get("id")
        if agent_id is None:
            continue
        target_options.append(f"agent:{agent_id} - {_agent_option_label(agent)}")
    for group in groups:
        group_id = group.get("id")
        if group_id is None:
            continue
        target_options.append(f"group:{group_id} - {_group_option_label(group)}")

    updated_fields = []
    for field in create_form.fields:
        if field.key != "chat_target":
            updated_fields.append(field)
            continue
        updated_fields.append(
            replace(
                field,
                options=tuple(target_options),
                default=target_options[0] if target_options else "",
            )
        )

    if not updated_fields:
        return spec

    return replace(spec, create_form=replace(create_form, fields=tuple(updated_fields)))


def _is_participant_view(selected_view: dict[str, object]) -> bool:
    return str(selected_view.get("view_id") or "").strip().endswith("participants.view")


def _render_participant_view_controls(
    *,
    spec: object,
    selected_view: dict[str, object],
    create_action: object | None,
    edit_target: dict[str, object] | None,
) -> None:
    del edit_target

    st.divider()
    st.subheader("Choose a chat target")
    st.caption("Pick an agent or a group first. New discussions are no longer created here.")

    if create_action is None:
        st.info("This module view does not currently expose chat target creation.")
        return

    try:
        agents = list_agents()
    except ApiError as error:
        st.error(f"Unable to load agents: {error.detail}")
        agents = []

    try:
        groups = list_groups()
    except ApiError as error:
        st.error(f"Unable to load groups: {error.detail}")
        groups = []

    try:
        model_configs = list_llm_configs()
    except ApiError as error:
        st.error(f"Unable to load model configs: {error.detail}")
        model_configs = []

    with st.container(border=True):
        st.write("Chat target")
        target_kind = st.radio(
            "Target type",
            options=("agent", "group"),
            horizontal=True,
            key=f"participant_target_kind:{spec.view_id}",
        )

        form_result = _render_participant_target_form(
            view_id=str(selected_view.get("view_id") or spec.view_id),
            title="",
            submit_label="Save target",
            target_kind=target_kind,
            agents=agents,
            groups=groups,
            model_configs=model_configs,
            initial_values=None,
            form_key=f"participant_create_form:{spec.view_id}",
        )
        if form_result is not None:
            submitted, cancelled, payload = form_result
            if cancelled:
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
                    st.error(f"Unable to create chat target: {error.detail}")
                else:
                    discussion_id = _activate_discussion_for_participant_target(payload)
                    st.success("Target saved.")
                    if discussion_id is not None:
                        st.session_state["selected_page"] = "discussion"
                        st.rerun()
                        return
                    st.rerun()
                    return

    with st.expander("Create a new group", expanded=False):
        st.caption("Group names must be unique and must follow the same naming rules used by Apmatia groups.")
        with st.form(f"participant_create_group_form:{spec.view_id}"):
            group_name = st.text_input("Group name", placeholder="My Project Team")
            group_description = st.text_area("Description", placeholder="Optional notes about the group's purpose.")
            group_submitted = st.form_submit_button("Create group", type="primary", use_container_width=True)
        if group_submitted:
            try:
                create_group(name=group_name, description=group_description)
            except ApiError as error:
                st.error(f"Unable to create group: {error.detail}")
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Group created.")
                st.rerun()


def _render_participant_target_form(
    *,
    view_id: str,
    title: str,
    submit_label: str,
    target_kind: str,
    agents: list[dict[str, object]],
    groups: list[dict[str, object]],
    model_configs: list[dict[str, object]],
    initial_values: dict[str, object] | None,
    form_key: str,
) -> tuple[bool, bool, dict[str, object]] | None:
    target_options = _participant_target_options(target_kind, agents=agents, groups=groups)
    if not target_options:
        st.warning("No chat targets are available yet.")
        return None

    initial_target = _participant_initial_target(initial_values)
    if target_kind == "agent":
        default_target = _default_option(target_options, initial_target, prefix="agent:")
    else:
        default_target = _default_option(target_options, initial_target, prefix="group:")
    default_model_id = _initial_model_id(initial_values)
    default_role = str((initial_values or {}).get("role") or "agent")
    default_temperature = _initial_float(initial_values, "temperature_override")

    model_options = [config for config in model_configs if config.get("id") is not None]
    tool_options = _tool_options()

    with st.form(form_key):
        if title:
            st.subheader(title)

        chat_target = st.selectbox(
            "Chat target",
            options=target_options,
            index=_option_index(target_options, default_target),
            help="Choose the agent or group Apmatia should follow.",
        )

        model_ids = [int(config["id"]) for config in model_options if config.get("id") is not None]
        model_lookup = {int(config["id"]): config for config in model_options if config.get("id") is not None}
        selected_model_id = None
        if model_ids:
            model_ids_with_none = [None] + model_ids
            try:
                model_index = model_ids_with_none.index(default_model_id)
            except ValueError:
                model_index = 0
            selected_model_id = st.selectbox(
                "Model alias",
                options=model_ids_with_none,
                index=model_index,
                format_func=lambda model_id: _model_option_label(model_id, model_lookup),
                help="Pick a model alias to use for this chat target.",
            )
        else:
            st.info("No model configs are available yet.")

        role = st.selectbox(
            "Role",
            options=("agent", "coordinator", "reviewer", "observer"),
            index=_option_index(["agent", "coordinator", "reviewer", "observer"], default_role),
            help="Controls how this chat target is treated when it is part of a discussion.",
        )

        payload: dict[str, object] = {
            "chat_target": chat_target,
            "role": role,
            "selected_model_id": selected_model_id,
        }

        if target_kind == "group":
            turn_policy = st.selectbox(
                "Turn policy",
                options=("manual", "auto", "round_robin", "coordinator_only"),
                index=_option_index(
                    ["manual", "auto", "round_robin", "coordinator_only"],
                    str((initial_values or {}).get("turn_policy") or "manual"),
                ),
                help="Group chats use a turn policy to decide how turns are scheduled.",
            )
            payload["turn_policy"] = turn_policy
        else:
            st.caption("Single-agent chats do not need an explicit turn policy.")

        if default_temperature is None:
            default_temperature = 0.0
        temperature_override = st.number_input(
            "Temperature override",
            min_value=0.0,
            max_value=2.0,
            value=float(default_temperature),
            step=0.1,
            format="%.1f",
            help="Optional runtime temperature override for this chat target.",
        )
        payload["temperature_override"] = temperature_override

        if tool_options:
            selected_tools = st.multiselect(
                "Tool restrictions",
                options=[option["id"] for option in tool_options],
                default=_initial_tool_ids(initial_values, tool_options),
                format_func=lambda tool_id: _tool_option_label(tool_id, tool_options),
                help="Select tools to disallow for this chat target.",
            )
            payload["tool_restrictions"] = [str(tool_id) for tool_id in selected_tools]
        else:
            st.caption("No tools are available to restrict yet.")

        submit_col, cancel_col = st.columns(2)
        with submit_col:
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
        with cancel_col:
            cancelled = st.form_submit_button("Reset", use_container_width=True)

    return submitted, cancelled, payload


def _participant_target_options(
    target_kind: str,
    *,
    agents: list[dict[str, object]],
    groups: list[dict[str, object]],
) -> list[str]:
    if target_kind == "group":
        return [
            f"group:{group.get('id')} - {_group_option_label(group)}"
            for group in groups
            if group.get("id") is not None
        ]
    return [
        f"agent:{agent.get('id')} - {_agent_option_label(agent)}"
        for agent in agents
        if agent.get("id") is not None
    ]


def _participant_initial_target(initial_values: dict[str, object] | None) -> str | None:
    if not isinstance(initial_values, dict):
        return None
    if initial_values.get("group_id") not in (None, ""):
        return f"group:{initial_values.get('group_id')}"
    if initial_values.get("agent_id") not in (None, ""):
        return f"agent:{initial_values.get('agent_id')}"
    return None


def _default_option(options: list[str], target: str | None, *, prefix: str) -> str:
    if target:
        for option in options:
            if str(option).startswith(target) or str(option).startswith(prefix) and str(option).split(" - ", 1)[0] == target:
                return option
    return options[0]


def _initial_model_id(initial_values: dict[str, object] | None) -> int | None:
    if not isinstance(initial_values, dict):
        return None
    value = initial_values.get("selected_model_id")
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _initial_float(initial_values: dict[str, object] | None, key: str) -> float | None:
    if not isinstance(initial_values, dict):
        return None
    value = initial_values.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _initial_tool_ids(initial_values: dict[str, object] | None, tool_options: list[dict[str, object]]) -> list[int]:
    if not isinstance(initial_values, dict):
        return []
    selected = {str(item).strip() for item in (initial_values.get("tool_restrictions") or []) if str(item).strip()}
    defaults: list[int] = []
    for tool in tool_options:
        tool_id = tool.get("id")
        if tool_id is None:
            continue
        tool_name = str(tool.get("name") or "").strip()
        if str(tool_id) in selected or tool_name in selected:
            defaults.append(int(tool_id))
    return defaults


def _tool_options() -> list[dict[str, object]]:
    try:
        return list_tool_definitions()
    except ApiError as error:
        st.error(f"Unable to load tools: {error.detail}")
        return []


def _model_option_label(model_id: object | None, lookup: dict[int, dict[str, object]]) -> str:
    if model_id in (None, ""):
        return "No override"
    try:
        resolved_id = int(model_id)
    except (TypeError, ValueError):
        return str(model_id)
    config = lookup.get(resolved_id)
    if config is None:
        return f"Model {resolved_id}"
    alias = str(config.get("user_alias") or config.get("name") or f"Model {resolved_id}").strip()
    provider = str(config.get("provider_name") or config.get("backend") or "").strip()
    if provider:
        return f"{alias} ({provider})"
    return alias


def _tool_option_label(tool_id: object | None, tools: list[dict[str, object]]) -> str:
    try:
        resolved_id = int(tool_id) if tool_id is not None else None
    except (TypeError, ValueError):
        resolved_id = None
    if resolved_id is None:
        return str(tool_id)
    for tool in tools:
        if int(tool.get("id") or -1) != resolved_id:
            continue
        name = str(tool.get("name") or f"Tool {resolved_id}").strip()
        provider = str(tool.get("provider_id") or "").strip()
        return f"{name} ({provider})" if provider else name
    return f"Tool {resolved_id}"


def _activate_discussion_for_participant_target(payload: dict[str, object]) -> str | None:
    chat_target = str(payload.get("chat_target") or "").strip()
    if not chat_target:
        return None

    target_reference = chat_target.split(" - ", 1)[0].strip()
    if ":" not in target_reference:
        return None

    target_kind, raw_target_id = target_reference.split(":", 1)
    target_kind = target_kind.strip().lower()
    try:
        target_id = int(raw_target_id)
    except (TypeError, ValueError):
        return None

    try:
        tree = discussion_tree()
    except ApiError as error:
        st.warning(f"Target saved, but the discussion thread could not be opened: {error.detail}")
        return None

    discussion = _matching_discussion_for_target(tree.get("discussions", []), target_kind, target_id)
    if discussion is not None:
        discussion_id = str(discussion.get("discussion_id") or "").strip()
        if discussion_id:
            try:
                open_discussion(discussion_id)
            except ApiError as error:
                st.warning(f"Target saved, but the discussion thread could not be opened: {error.detail}")
                return None
            st.session_state["discussion_selected_agent_id"] = target_id if target_kind == "agent" else None
            return discussion_id

    discussion_title = chat_target.split(" - ", 1)[-1].strip() or f"{target_kind.title()} {target_id}"
    create_payload: dict[str, object] = {
        "title": discussion_title,
        "chat_mode": "single",
    }
    if target_kind == "agent":
        create_payload["agent_id"] = target_id
        create_payload["participant_agent_ids"] = [target_id]
        st.session_state["discussion_selected_agent_id"] = target_id
    elif target_kind == "group":
        create_payload["group_id"] = target_id
        st.session_state["discussion_selected_agent_id"] = None
    else:
        return None

    try:
        created = create_discussion(**create_payload)
    except ApiError as error:
        st.warning(f"Target saved, but a discussion could not be created: {error.detail}")
        return None

    discussion_id = str(created.get("discussion", {}).get("discussion_id") or "").strip()
    if not discussion_id:
        return None

    try:
        open_discussion(discussion_id)
    except ApiError as error:
        st.warning(f"Target saved, but the discussion thread could not be opened: {error.detail}")
        return None
    return discussion_id


def _matching_discussion_for_target(
    discussions: Iterable[object],
    target_kind: str,
    target_id: int,
) -> dict[str, object] | None:
    for discussion in discussions:
        if not isinstance(discussion, dict):
            continue
        if target_kind == "group":
            if _safe_int(discussion.get("group_id"), default=None) == target_id:
                return discussion
            continue

        participant_agent_ids = discussion.get("participant_agent_ids") or []
        try:
            normalized_participants = {
                int(candidate)
                for candidate in participant_agent_ids
                if candidate is not None
            }
        except (TypeError, ValueError):
            normalized_participants = set()
        if target_id in normalized_participants:
            return discussion
    return None


def _safe_int(value: object | None, *, default: int | None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _option_index(options: list[object], selected: object | None) -> int:
    if selected is None:
        return 0
    for index, option in enumerate(options):
        if option == selected:
            return index
        if str(option) == str(selected):
            return index
    return 0


def _agent_option_label(agent: dict[str, object]) -> str:
    name = str(agent.get("name") or "").strip()
    if name:
        return name
    agent_id = agent.get("id")
    return f"Agent {agent_id}" if agent_id is not None else "Agent"


def _group_option_label(group: dict[str, object]) -> str:
    name = str(group.get("name") or "").strip()
    if name:
        return name
    group_id = group.get("id")
    return f"Group {group_id}" if group_id is not None else "Group"


def _edit_target_missing(target: dict[str, object], items: Iterable[object]) -> bool:
    return _delete_target_missing(target, items)


def _disable_target_missing(target: dict[str, object], items: Iterable[object]) -> bool:
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
