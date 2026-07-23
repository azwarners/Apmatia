"""Generic module view page for rendering registry-backed module views."""
from __future__ import annotations

from dataclasses import replace
import json
import re
from collections.abc import Iterable
from datetime import date, datetime, time

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_discussion,
    create_group,
    execute_module_command,
    list_agents,
    list_groups,
    list_llm_configs,
    list_module_view_items,
    list_modules,
    list_tool_definitions,
    open_discussion,
    start_loop_task,
)
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.renderers import (
    render_collection_view,
    render_module_view,
    render_module_view_form,
    render_navigation_pane,
)
from apmatia.interfaces.streamlit.components.shell_tabs import render_shell_tabs
from apmatia.interfaces.streamlit.components.terminal_output import render_terminal_block
from apmatia.interfaces.streamlit.page_runtime import current_page_generation, is_current_page_generation
from apmatia.modules.agent_loops.prompt_helpers import parse_checklist_text


TERMINAL_HEIGHT_PX = 720


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

    if str(selected_module.get("module_id") or "") == "agent_loops":
        _render_agent_loops_shell(selected_module)
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
    spec = _enrich_agent_alarm_view(spec, selected_view)
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
        if intent.intent == "save":
            command_id = str(intent.payload.get("command_id") or "").strip()
            if not command_id:
                st.warning("Save is not configured for this module view.")
                continue
            payload = {key: value for key, value in intent.payload.items() if key != "command_id"}
            try:
                result = execute_module_command(command_id, **_json_safe_payload(payload))
            except ApiError as error:
                st.error(f"Unable to save configuration: {error.detail}")
            else:
                _display_module_command_result(result, default_success="Configuration saved.")
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
                    result = execute_module_command(command_id, item_id=item_id, **_json_safe_payload(payload))
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
                    result = execute_module_command(command_id, item_id=item_id, **_json_safe_payload(payload))
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
                result = execute_module_command(command_id, **_json_safe_payload(payload))
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
                execute_module_command(command_id, **_json_safe_payload(payload))
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


def _display_module_command_result(result: object, *, default_success: str) -> None:
    if not isinstance(result, dict):
        st.success(default_success)
        return

    warning = str(result.get("warning") or "").strip()
    warnings = result.get("warnings")
    message = str(result.get("message") or "").strip()
    if warning:
        st.warning(warning)
    if isinstance(warnings, list):
        for entry in warnings:
            text = str(entry or "").strip()
            if text:
                st.warning(text)
    if message:
        st.success(message)
    else:
        st.success(default_success)


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


def _enrich_agent_alarm_view(
    spec: object,
    selected_view: dict[str, object],
):
    if str(selected_view.get("view_id") or "").strip() != "agent_alarms.alarms.view":
        return spec

    create_form = getattr(spec, "create_form", None)
    edit_form = getattr(spec, "edit_form", None)
    if create_form is None and edit_form is None:
        return spec

    try:
        agents = list_agents()
    except ApiError:
        agents = []
    try:
        model_configs = list_llm_configs()
    except ApiError:
        model_configs = []

    agent_options = tuple(
        {
            "label": _alarm_agent_option_label(agent),
            "value": agent.get("id"),
        }
        for agent in agents
        if isinstance(agent, dict) and agent.get("id") is not None
    )
    model_options = tuple(
        {
            "label": _alarm_model_option_label(config),
            "value": config.get("id"),
        }
        for config in model_configs
        if isinstance(config, dict) and config.get("id") is not None
    )

    if create_form is not None:
        create_form = _replace_alarm_form_options(create_form, agent_options, model_options)
    if edit_form is not None:
        edit_form = _replace_alarm_form_options(edit_form, agent_options, model_options)
    return replace(spec, create_form=create_form, edit_form=edit_form)


def _replace_alarm_form_options(form, agent_options: tuple[dict[str, object], ...], model_options: tuple[dict[str, object], ...]):
    updated_fields = []
    for field in form.fields:
        if field.key == "agent_id":
            updated_fields.append(replace(field, options=agent_options))
            continue
        if field.key == "model_id":
            updated_fields.append(replace(field, options=model_options))
            continue
        updated_fields.append(field)
    return replace(form, fields=tuple(updated_fields))


def _alarm_agent_option_label(agent: dict[str, object]) -> str:
    name = str(agent.get("name") or "").strip()
    return name or "Unnamed agent"


def _alarm_model_option_label(config: dict[str, object]) -> str:
    alias = str(config.get("user_alias") or "").strip()
    if alias:
        return alias
    name = str(config.get("name") or "").strip()
    if name:
        return name
    provider_name = str(config.get("provider_name") or "").strip()
    return provider_name or "Unnamed model"


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
                    execute_module_command(command_id, **_json_safe_payload(payload))
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
                    str((initial_values or {}).get("turn_policy") or "round_robin"),
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

    discussion_title = chat_target.split(" - ", 1)[-1].strip() or f"{target_kind.title()} {target_id}"
    create_payload: dict[str, object] = {
        "title": discussion_title,
        "chat_mode": "round_robin",
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


def _render_agent_loops_shell(selected_module: dict[str, object]) -> None:
    page_generation = current_page_generation()
    st.markdown(
        """
        <style>
            html,
            body {
                height: 100%;
                overflow: hidden;
            }

            div[data-testid="stAppViewContainer"] {
                height: 100vh;
                overflow: hidden;
            }

            div[data-testid="stAppViewContainer"] > .main,
            div[data-testid="stMain"] {
                height: 100vh;
                overflow: hidden;
            }

            div[data-testid="stMainBlockContainer"] {
                max-width: none;
                height: 100vh;
                min-height: 0;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                padding-top: 0.5rem;
                padding-right: 1rem;
                padding-bottom: 0.5rem;
                padding-left: 1rem;
            }

            div[data-testid="stVerticalBlock"] {
                min-height: 0;
            }

            div[data-testid="stVerticalBlock"] > div {
                min-height: 0;
            }

            div[data-testid="stVerticalBlock"] {
                gap: 0.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _render_agent_loops_terminal_styles()
    views_by_type = _agent_loops_views_by_type(selected_module)
    contacts_view = views_by_type.get("contact")
    runs_view = views_by_type.get("run")
    workspace_view = views_by_type.get("workspace")
    knowledge_view = views_by_type.get("knowledge")
    if contacts_view is None or runs_view is None or workspace_view is None or knowledge_view is None:
        st.title(str(selected_module.get("name") or "Agent Loops"))
        st.info("Agent Loops is missing one or more expected views.")
        return

    contact_items = list_module_view_items(str(contacts_view.get("view_id") or ""))

    sidebar_rendered = bool(st.session_state.get("agent_loops_shell_sidebar_rendered"))
    selected_contact_id = str(st.session_state.get("agent_loops_selected_contact_id") or "").strip()
    valid_contact_ids = {str(item.get("id") or "").strip() for item in contact_items if str(item.get("id") or "").strip()}
    if not sidebar_rendered and (not selected_contact_id or selected_contact_id not in valid_contact_ids):
        selected_contact_id = next(iter(valid_contact_ids), "")
        if selected_contact_id:
            st.session_state["agent_loops_selected_contact_id"] = selected_contact_id

    if not sidebar_rendered:
        nav_spec = adapt_module_view(contacts_view, items=contact_items)
        nav_choice = render_navigation_pane(nav_spec, items=contact_items, active_item_id=selected_contact_id or None)
        if nav_choice == "__exit__":
            _exit_agent_loops_shell()
            st.rerun()
            return
        if nav_choice:
            st.session_state["agent_loops_selected_contact_id"] = nav_choice
            st.rerun()
            return

    selected_contact = next((item for item in contact_items if str(item.get("id") or "") == selected_contact_id), None)
    if selected_contact is None:
        st.title(str(selected_module.get("name") or "Agent Loops"))
        st.info("Pick an agent or group from the sidebar to view its task workspace.")
        return

    contact_kind = str(selected_contact.get("contact_kind") or "").strip().lower()
    contact_id = selected_contact.get("contact_id")
    roots = _selected_contact_roots(contact_kind, contact_id)

    task_items = _filter_agent_loops_tasks(
        list_module_view_items(str(runs_view.get("view_id") or "")),
        contact_kind=contact_kind,
        contact_id=contact_id,
    )
    workspace_items = _filter_agent_loops_files(
        list_module_view_items(str(workspace_view.get("view_id") or "")),
        root_path=str(roots["workspace_root"]),
    )
    knowledge_items = _filter_agent_loops_files(
        list_module_view_items(str(knowledge_view.get("view_id") or "")),
        root_path=str(roots["knowledge_root"]),
    )

    launch_form_key = f"agent_loops_task_form_open:{selected_contact_id}"
    launch_form_widget_key = f"agent_loops_task_form:{selected_contact_id}"
    selected_task_key = f"agent_loops_selected_task_id:{selected_contact_id}"
    polling_state_key = f"agent_loops_current_task_polling:{selected_contact_id}"
    selected_task_id = str(st.session_state.get(selected_task_key) or "").strip()
    current_task = _selected_agent_loops_task(task_items, selected_task_id=selected_task_id)
    if current_task is not None:
        current_task_id = str(current_task.get("task_id") or current_task.get("id") or "").strip()
        if current_task_id and selected_task_id != current_task_id:
            st.session_state[selected_task_key] = current_task_id

    current_task_status = str(current_task.get("status") or "") if isinstance(current_task, dict) else ""
    current_task_status = current_task_status.strip().lower()
    should_poll_current_task = current_task is not None and current_task_status in {"running", "stopping"}
    if should_poll_current_task:
        st.session_state[polling_state_key] = True
    elif polling_state_key in st.session_state:
        st.session_state[polling_state_key] = False

    selected_tab = render_shell_tabs(
        ("Current Task", "Task History", "Workspace", "Knowledge"),
        key=f"agent_loops_shell_tab:{selected_contact_id}",
        default="Current Task",
    )

    if selected_tab == "Current Task":
        toolbar_columns = st.columns([1, 1, 1, 6, 1.4], vertical_alignment="center")
        with toolbar_columns[4]:
            new_task_clicked = st.button(
                "New Task",
                key=f"agent_loops_new_task:{selected_contact_id}",
                use_container_width=True,
            )
        if new_task_clicked:
            st.session_state[launch_form_key] = True

        def _render_current_task_content() -> dict[str, object]:
            current_items = _filter_agent_loops_tasks(
                list_module_view_items(str(runs_view.get("view_id") or "")),
                contact_kind=contact_kind,
                contact_id=contact_id,
            )
            refreshed_task = _selected_agent_loops_task(
                current_items,
                selected_task_id=str(st.session_state.get(selected_task_key) or "").strip(),
            )
            with st.container(border=True, key="agent-loops-shell-content"):
                if st.session_state.get(launch_form_key):
                    _render_agent_loops_task_form(
                        selected_contact=selected_contact,
                        roots=roots,
                        form_key=launch_form_widget_key,
                        state_key=launch_form_key,
                    )
                elif refreshed_task is None:
                    st.info("No task has been recorded for this contact yet.")
                else:
                    _render_agent_loops_current_task_output(refreshed_task, roots=roots)
            return {"running": bool(refreshed_task and str(refreshed_task.get("status") or "").strip().lower() in {"running", "stopping"})}

        fragment_factory = getattr(st, "fragment", None)
        should_use_live_fragment = bool(st.session_state.get(polling_state_key)) and getattr(fragment_factory, "__module__", "").startswith("streamlit")

        if should_use_live_fragment:
            @fragment_factory(run_every=0.5)
            def _current_task_fragment() -> dict[str, object]:
                if not is_current_page_generation(page_generation):
                    st.empty()
                    return {"running": False}
                current_items = _filter_agent_loops_tasks(
                    list_module_view_items(str(runs_view.get("view_id") or "")),
                    contact_kind=contact_kind,
                    contact_id=contact_id,
                )
                refreshed_task = _selected_agent_loops_task(
                    current_items,
                    selected_task_id=str(st.session_state.get(selected_task_key) or "").strip(),
                )
                if refreshed_task is None:
                    st.info("No task has been recorded for this contact yet.")
                    st.session_state[polling_state_key] = False
                    st.rerun()
                    return {"running": False}
                _render_agent_loops_current_task_output(refreshed_task, roots=roots)
                refreshed_status = str(refreshed_task.get("status") or "").strip().lower()
                still_running = refreshed_status in {"running", "stopping"}
                if not still_running:
                    st.session_state[polling_state_key] = False
                    st.rerun()
                return {"running": still_running}

            _current_task_fragment()
        else:
            _render_current_task_content()

    elif selected_tab == "Task History":
        if any(str(item.get("status") or "").strip().lower() == "running" for item in task_items):
            fragment_factory = getattr(st, "fragment", None)
            if getattr(fragment_factory, "__module__", "").startswith("streamlit"):
                @fragment_factory(run_every=0.5)
                def _task_history_fragment() -> dict[str, object]:
                    if not is_current_page_generation(page_generation):
                        st.empty()
                        return {"running": False}
                    current_items = _filter_agent_loops_tasks(
                        list_module_view_items(str(runs_view.get("view_id") or "")),
                        contact_kind=contact_kind,
                        contact_id=contact_id,
                    )
                    _render_agent_loops_task_history(current_items, roots=roots)
                    return {"running": True}

                _task_history_fragment()
            else:
                _render_agent_loops_task_history(task_items, roots=roots)
        else:
            _render_agent_loops_task_history(task_items, roots=roots)

    elif selected_tab == "Workspace":
        _render_agent_loops_collection_tab(workspace_view, workspace_items)

    else:
        _render_agent_loops_collection_tab(knowledge_view, knowledge_items)


def _render_agent_loops_collection_tab(view: dict[str, object], items: list[dict[str, object]]) -> None:
    spec = adapt_module_view(view, items=items)
    render_collection_view(replace(spec, title="", caption="", description=""))


def _selected_agent_loops_task(
    items: list[dict[str, object]],
    *,
    selected_task_id: str | None = None,
) -> dict[str, object] | None:
    if not items:
        return None

    if selected_task_id:
        selected = next(
            (
                item
                for item in items
                if str(item.get("task_id") or item.get("id") or "").strip() == selected_task_id
            ),
            None,
        )
        if selected is not None:
            return selected

    def _task_sort_key(item: dict[str, object]) -> tuple[int, str]:
        status = str(item.get("status") or "").strip().lower()
        priority = 0 if status in {"running", "stopping"} else 1
        return priority, str(item.get("updated_at") or "")

    return sorted(items, key=_task_sort_key)[0]


def _render_agent_loops_current_task_output(item: dict[str, object], *, roots: dict[str, object]) -> None:
    task_id = str(item.get("task_id") or item.get("id") or "").strip()
    status = str(item.get("status") or "queued").strip().lower()
    _render_agent_loops_live_output(item, task_id=task_id, roots=roots, body_height=520)

    if status in {"running", "stopping"}:
        st.caption("The current task is still active and can be stopped from the task history tab.")


def _render_agent_loops_task_history(items: list[dict[str, object]], *, roots: dict[str, object]) -> None:
    if not items:
        st.info("No previous tasks have been recorded for this contact yet.")
        return

    def _task_sort_key(item: dict[str, object]) -> tuple[int, str]:
        status = str(item.get("status") or "").strip().lower()
        priority = 0 if status in {"running", "stopping"} else 1
        return priority, str(item.get("updated_at") or "")

    items = sorted(items, key=_task_sort_key)
    st.caption("Each task expands into its own progress record, summary, and executive analysis.")
    for index, item in enumerate(items):
        title = str(item.get("title") or f"Task {index + 1}").strip()
        status = str(item.get("status") or "queued").strip()
        prompt = str(item.get("prompt") or "").strip()
        summary = str(item.get("summary") or "").strip()
        contact = str(item.get("contact") or "").strip()
        mode = str(item.get("mode") or "single").strip()
        updated_at = str(item.get("updated_at") or "").strip()
        task_id = str(item.get("task_id") or item.get("id") or "").strip()
        task_header = f"{title} · {status}"
        is_active = index == 0 and status in {"running", "stopping"}
        if is_active:
            with st.container(border=True):
                _render_agent_loops_status_banner(status=status)
                st.markdown(f"### {task_header}")
                if contact:
                    st.caption(contact)
                if updated_at:
                    st.caption(f"Updated {updated_at}")
                st.caption(f"Mode: {mode}")
                if task_id:
                    st.caption(f"Task ID: {task_id}")
                control_left, control_right = st.columns([1, 5])
                with control_left:
                    if status in {"running", "stopping"}:
                        if st.button(
                            "Stop task",
                            key=f"agent_loops_stop_task:{item.get('task_id') or index}",
                            type="secondary",
                        ):
                            task_id = str(item.get("task_id") or "").strip()
                            if task_id:
                                try:
                                    execute_module_command("agent_loops.tasks.stop", task_id=task_id)
                                except ApiError as error:
                                    st.error(f"Unable to stop task: {error.detail}")
                                else:
                                    st.success("Stop requested.")
                                    st.rerun()
                with control_right:
                    if status in {"running", "stopping"}:
                        st.caption("The loop is currently running and can be interrupted here.")
                if status in {"running", "stopping"}:
                    _render_agent_loops_live_output(
                        item,
                        task_id=task_id,
                        roots=roots,
                        body_height=520,
                    )
                if summary:
                    _render_agent_loops_terminal_block(
                        title="Summary",
                        body=summary,
                        subtitle="The current progress summary for this task.",
                    )
                executive_analysis = str(item.get("executive_analysis") or "").strip()
                if executive_analysis:
                    _render_agent_loops_terminal_block(
                        title="Executive analysis",
                        body=executive_analysis,
                        subtitle="The user-facing handoff for this task.",
                    )
                last_error = str(item.get("last_error") or "").strip()
                if last_error:
                    st.error(last_error)
                current_iteration = item.get("current_iteration")
                max_iterations = item.get("max_iterations")
                if current_iteration is not None and max_iterations is not None:
                    st.caption(f"Iteration {current_iteration} of {max_iterations}")
                if item.get("workspace_root"):
                    st.caption(f"Workspace root: {item.get('workspace_root')}")
                elif roots.get("workspace_root"):
                    st.caption(f"Workspace root: {roots['workspace_root']}")
                if item.get("knowledge_root"):
                    st.caption(f"Knowledge root: {item.get('knowledge_root')}")
                elif roots.get("knowledge_root"):
                    st.caption(f"Knowledge root: {roots['knowledge_root']}")
        else:
            with st.expander(task_header, expanded=False):
                if contact:
                    st.caption(contact)
                if updated_at:
                    st.caption(f"Updated {updated_at}")
                st.caption(f"Mode: {mode}")
                if task_id:
                    st.caption(f"Task ID: {task_id}")
                if prompt:
                    _render_agent_loops_terminal_block(
                        title="Task prompt",
                        body=prompt,
                        subtitle="The prompt that launched this loop.",
                    )
                if summary:
                    _render_agent_loops_terminal_block(
                        title="Summary",
                        body=summary,
                        subtitle="The current progress summary for this task.",
                    )
                executive_analysis = str(item.get("executive_analysis") or "").strip()
                if executive_analysis:
                    _render_agent_loops_terminal_block(
                        title="Executive analysis",
                        body=executive_analysis,
                        subtitle="The user-facing handoff for this task.",
                    )
                last_error = str(item.get("last_error") or "").strip()
                if last_error:
                    st.error(last_error)
                current_iteration = item.get("current_iteration")
                max_iterations = item.get("max_iterations")
                if current_iteration is not None and max_iterations is not None:
                    st.caption(f"Iteration {current_iteration} of {max_iterations}")
                if item.get("workspace_root"):
                    st.caption(f"Workspace root: {item.get('workspace_root')}")
                elif roots.get("workspace_root"):
                    st.caption(f"Workspace root: {roots['workspace_root']}")
                if item.get("knowledge_root"):
                    st.caption(f"Knowledge root: {item.get('knowledge_root')}")
                elif roots.get("knowledge_root"):
                    st.caption(f"Knowledge root: {roots['knowledge_root']}")


def _render_agent_loops_task_transcript(task_id: str, discussion_id: str | None = None) -> None:
    """Compatibility shim for older tests and call sites.

    The agent-loop task history no longer renders transcript message cards in the UI.
    This helper is intentionally a no-op so older tests can still patch it.
    """
    _ = task_id, discussion_id


def _render_agent_loops_live_output(
    item: dict[str, object],
    *,
    task_id: str,
    roots: dict[str, object],
    body_height: str | int = "content",
) -> None:
    prompt = str(item.get("prompt") or "").strip()
    checklist = item.get("checklist") if isinstance(item.get("checklist"), list) else []
    loop_status = item.get("loop_status") if isinstance(item.get("loop_status"), dict) else {}

    live_lines: list[str] = [
        "PROMPT",
        prompt or "(no prompt provided)",
    ]
    if task_id:
        live_lines.append(f"TASK {task_id}")
    if checklist:
        live_lines.append("")
        live_lines.append("CHECKLIST")
        live_lines.extend(_format_agent_loops_checklist_lines(checklist, loop_status))

    event_stream_lines = _agent_loop_event_stream_lines(item, task_id=task_id)
    if event_stream_lines:
        live_lines.append("")
        live_lines.append("EVENT STREAM")
        live_lines.extend(event_stream_lines)

    _render_agent_loops_terminal_block(
        title="Live output",
        body="\n".join(live_lines),
        subtitle="Append-only stream for the active loop.",
        prompt=f"loop@{task_id[:8] or 'session'}$",
        status=str(item.get("status") or "RUNNING").upper(),
        body_height=body_height,
    )

    return


def _agent_loop_event_stream_lines(item: dict[str, object], *, task_id: str) -> list[str]:
    lines: list[str] = []
    task_lines: list[str] = []
    tool_lines: list[str] = []

    events = item.get("events") if isinstance(item.get("events"), list) else []
    if events:
        for index, event in enumerate(events, start=1):
            if not isinstance(event, dict):
                continue
            payload = _loop_event_payload(event)
            event_type = str(
                event.get("type")
                or event.get("event_type")
                or payload.get("type")
                or payload.get("event_type")
                or "event"
            ).strip().lower()
            if event_type == "task_started":
                title = str(payload.get("title") or "").strip()
                contact_kind = str(payload.get("contact_kind") or "").strip()
                contact_id = str(payload.get("contact_id") or "").strip()
                task_lines.append(f"{index:02d} TASK STARTED")
                if title:
                    task_lines.append(f"Title: {title}")
                if contact_kind or contact_id:
                    task_lines.append(f"Target: {contact_kind} {contact_id}".strip())
            elif event_type == "model_turn_started":
                turn_index = payload.get("turn_index")
                if turn_index is not None:
                    task_lines.append(f"{index:02d} TURN STARTED")
                    task_lines.append(f"Turn: {turn_index}")
            elif event_type == "model_activity":
                continue
            elif event_type == "model_turn_completed":
                final_text = _strip_loop_status_markup(str(payload.get("final_text") or "").strip())
                if final_text:
                    task_lines.append(f"{index:02d} TURN COMPLETED")
                    task_lines.append("Final response:")
                    task_lines.extend(_indent_block(final_text))
                loop_status = payload.get("loop_status")
                if isinstance(loop_status, dict) and loop_status:
                    checklist_lines = _format_agent_loops_checklist_lines(
                        item.get("checklist") if isinstance(item.get("checklist"), list) else [],
                        loop_status,
                    )
                    if checklist_lines:
                        task_lines.append("CHECKLIST")
                        task_lines.extend(checklist_lines)
                    loop_status_lines = _format_loop_status_detail_lines(loop_status)
                    if loop_status_lines:
                        task_lines.extend(loop_status_lines)
                usage = payload.get("usage")
                tool_requests = payload.get("tool_requests")
                if usage not in (None, {}, []):
                    task_lines.append("USAGE")
                    task_lines.append(json.dumps(usage, indent=2, ensure_ascii=False))
                if tool_requests not in (None, {}, []):
                    task_lines.append("TOOL REQUESTS")
                    task_lines.append(json.dumps(tool_requests, indent=2, ensure_ascii=False))
            elif event_type == "tool_requested":
                tool_name = str(payload.get("tool_name") or "").strip()
                call_id = str(payload.get("call_id") or "").strip()
                arguments = payload.get("arguments")
                tool_lines.append(f"{index:02d} TOOL REQUESTED")
                if tool_name:
                    tool_lines.append(f"Tool: {tool_name}")
                if call_id:
                    tool_lines.append(f"Call: {call_id}")
                if arguments not in (None, {}, []):
                    tool_lines.append("Arguments:")
                    tool_lines.append(json.dumps(arguments, indent=2, ensure_ascii=False))
            elif event_type in {"tool_completed", "tool_failed"}:
                tool_name = str(payload.get("tool_name") or "").strip()
                call_id = str(payload.get("call_id") or "").strip()
                status = str(payload.get("status") or "").strip()
                output = payload.get("output")
                error = str(payload.get("error") or "").strip()
                metadata_payload = payload.get("metadata")
                tool_lines.append(f"{index:02d} {'TOOL COMPLETED' if event_type == 'tool_completed' else 'TOOL FAILED'}")
                if tool_name:
                    tool_lines.append(f"Tool: {tool_name}")
                if call_id:
                    tool_lines.append(f"Call: {call_id}")
                if status:
                    tool_lines.append(f"Status: {status}")
                if output not in (None, "", {}, []):
                    tool_lines.append("Output:")
                    if isinstance(output, (dict, list)):
                        tool_lines.append(json.dumps(output, indent=2, ensure_ascii=False))
                    else:
                        tool_lines.append(str(output))
                if error:
                    tool_lines.append("Error:")
                    tool_lines.append(error)
                if metadata_payload not in (None, {}, []):
                    tool_lines.append("Metadata:")
                    tool_lines.append(json.dumps(metadata_payload, indent=2, ensure_ascii=False))
            elif event_type == "task_completed":
                final_text = _strip_loop_status_markup(str(payload.get("final_text") or "").strip())
                if final_text:
                    task_lines.append(f"{index:02d} TASK COMPLETED")
                    task_lines.append("Final response:")
                    task_lines.extend(_indent_block(final_text))
            elif event_type == "task_failed":
                error = str(payload.get("error") or "").strip()
                if error:
                    task_lines.append(f"{index:02d} TASK FAILED")
                    task_lines.append(f"Error: {error}")
            elif event_type == "execution_limit_reached":
                stop_reason = str(payload.get("stop_reason") or "").strip()
                if stop_reason:
                    task_lines.append(f"{index:02d} EXECUTION LIMIT REACHED")
                    task_lines.append(f"Stop reason: {stop_reason}")
            elif event_type == "cancellation_requested":
                task_lines.append(f"{index:02d} CANCELLATION REQUESTED")
            else:
                if payload not in (None, {}, []):
                    if isinstance(payload, (dict, list)):
                        task_lines.append(json.dumps(payload, indent=2, ensure_ascii=False))
                    else:
                        task_lines.append(str(payload))

    if task_lines:
        lines.extend(task_lines)
        lines.append("")

    if tool_lines:
        lines.append("TOOL ACTIVITY")
        lines.extend(tool_lines)
        lines.append("")

    return lines[:-1] if lines and not lines[-1] else lines


def _indent_block(text: str, *, prefix: str = "") -> list[str]:
    lines = str(text or "").splitlines()
    if not lines:
        return [prefix.rstrip()]
    return [f"{prefix}{line}" if prefix else line for line in lines]


def _strip_loop_status_markup(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<loop_status>\s*(?P<payload>.+?)\s*</loop_status>", "", text, flags=re.DOTALL).strip()


def _format_agent_loops_checklist_lines(
    checklist: list[dict[str, object]],
    loop_status: dict[str, object],
) -> list[str]:
    completed_items = {
        str(candidate).strip()
        for candidate in (loop_status.get("completed_items") or [])
        if str(candidate).strip()
    }
    remaining_items = {
        str(candidate).strip()
        for candidate in (loop_status.get("remaining_items") or [])
        if str(candidate).strip()
    }

    source_checklist = checklist
    if not source_checklist and (completed_items or remaining_items):
        ordered_labels: list[str] = []
        for label in list(completed_items) + list(remaining_items):
            if label and label not in ordered_labels:
                ordered_labels.append(label)
        source_checklist = [{"label": label} for label in ordered_labels]

    checklist_lines: list[str] = []
    for raw_index, raw_item in enumerate(source_checklist, start=1):
        if not isinstance(raw_item, dict):
            continue
        label = str(raw_item.get("label") or raw_item.get("title") or raw_item.get("text") or f"Item {raw_index}").strip()
        if not label:
            continue
        if label in completed_items:
            checklist_lines.append(f"✅ {label}")
        elif label in remaining_items:
            checklist_lines.append(f"• {label}")
        else:
            checklist_lines.append(f"• {label}")

    return checklist_lines


def _render_agent_loops_task_progress(item: dict[str, object]) -> None:
    checklist = item.get("checklist") if isinstance(item.get("checklist"), list) else []
    loop_status = item.get("loop_status") if isinstance(item.get("loop_status"), dict) else {}
    if not checklist and not loop_status:
        return

    checklist_lines = _format_agent_loops_checklist_lines(checklist, loop_status)

    if checklist_lines:
        _render_agent_loops_terminal_block(
            title="Checklist progress",
            body="\n".join(checklist_lines),
            subtitle="Append-only checklist state for the active loop.",
            prompt="checklist$",
            status="OPEN",
        )


def _format_loop_status_detail_lines(loop_status: dict[str, object]) -> list[str]:
    lines: list[str] = []
    summary = str(loop_status.get("summary") or "").strip()
    next_action = str(loop_status.get("next_action") or "").strip()
    executive_analysis = str(loop_status.get("executive_analysis") or "").strip()

    if summary:
        lines.append("Summary:")
        lines.extend(_indent_block(summary))
    if next_action:
        if lines:
            lines.append("")
        lines.append("Next action:")
        lines.extend(_indent_block(next_action))
    if executive_analysis:
        if lines:
            lines.append("")
        lines.append("Executive analysis:")
        lines.extend(_indent_block(executive_analysis))
    return lines


def _loop_event_payload(event: object) -> dict[str, object]:
    if not isinstance(event, dict):
        return {}
    payload = event.get("payload")
    if isinstance(payload, dict):
        merged: dict[str, object] = dict(payload)
    elif isinstance(event.get("data"), dict):
        merged = dict(event.get("data") or {})
    else:
        merged = {}
    for key, value in event.items():
        if key in {"payload", "data", "created_at", "event_type", "type"}:
            continue
        merged.setdefault(key, value)
    return merged


def _render_agent_loops_execution_log(item: dict[str, object]) -> None:
    events = item.get("events") if isinstance(item.get("events"), list) else []
    if not events:
        return

    with st.expander("Execution log", expanded=False):
        for index, event in enumerate(events, start=1):
            if not isinstance(event, dict):
                continue
            payload = _loop_event_payload(event)
            event_type = str(
                event.get("type")
                or event.get("event_type")
                or payload.get("type")
                or payload.get("event_type")
                or "event"
            ).strip()
            event_lines: list[str] = [f"{index}. {event_type}"]
            if event_type == "task_started":
                event_lines.append(f"Task prepared for {payload.get('contact_kind')} {payload.get('contact_id')}.")
            elif event_type == "iteration_started":
                event_lines.append(f"Iteration {payload.get('iteration')} of {payload.get('max_iterations')} started.")
            elif event_type == "loop_status":
                status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
                status_lines = _format_loop_status_detail_lines(status)
                if status_lines:
                    event_lines.extend(status_lines)
                else:
                    event_lines.append("No readable loop status was provided.")
            elif event_type == "model_activity":
                event_lines.append(str(payload.get("text") or payload or "streamed activity"))
            else:
                event_lines.append(str(payload or event))
            _render_agent_loops_terminal_block(
                title="Execution log entry",
                body="\n".join(event_lines),
                subtitle="Append-only loop event history.",
                prompt=f"log[{index}]$",
                status="EVENT",
            )


def _render_agent_loops_event_log(item: dict[str, object]) -> None:
    _render_agent_loops_execution_log(item)

def _render_agent_loops_task_form(
    *,
    selected_contact: dict[str, object],
    roots: dict[str, object],
    form_key: str,
    state_key: str,
) -> None:
    contact_kind = str(selected_contact.get("contact_kind") or "").strip().lower()
    contact_id = selected_contact.get("contact_id")
    contact_label = str(selected_contact.get("title") or selected_contact.get("id") or "Contact")
    contact_id_int = _safe_int(contact_id)
    title_default = f"{contact_label} Task"

    agent_options: list[dict[str, object]] = []
    if contact_kind == "group":
        try:
            agent_options = list_agents()
        except ApiError as error:
            st.error(f"Unable to load agents for task launch: {error.detail}")
            return

    st.subheader("New Task")
    st.caption("Launch a long-running task loop for the selected contact.")
    with st.form(form_key):
        task_title = st.text_input("Task title", value=title_default)
        task_prompt = st.text_area(
            "Task prompt",
            value="",
            placeholder=f"What should {contact_label} work on?",
            height=160,
        )
        checklist_text = st.text_area(
            "Checklist (optional)",
            value="",
            placeholder="One item per line.",
            height=120,
        )
        allow_tools = st.checkbox("Allow tools", value=True)
        max_iterations = st.number_input("Max iterations", min_value=1, max_value=100, value=10, step=1)
        participant_agent_ids: list[int] = []
        if contact_kind == "group":
            participant_ids = st.multiselect(
                "Participants",
                options=[_safe_int(agent.get("id")) for agent in agent_options if _safe_int(agent.get("id")) is not None],
                default=[_safe_int(agent.get("id")) for agent in agent_options if _safe_int(agent.get("id")) is not None],
                format_func=lambda agent_id: _agent_option_label(agent_id, agent_options),
            )
            participant_agent_ids = [int(candidate) for candidate in participant_ids if candidate is not None]
            if not participant_agent_ids:
                st.caption("Pick at least one agent for the group task.")
        submitted = st.form_submit_button("Start task", type="primary", use_container_width=True)
        cancelled = st.form_submit_button("Cancel", use_container_width=True)

    if cancelled:
        st.session_state.pop(state_key, None)
        st.rerun()
        return
    if not submitted:
        return
    if not str(task_prompt).strip():
        st.error("Task prompt is required.")
        return
    if contact_kind == "group" and not participant_agent_ids:
        st.error("Select at least one participant for the group task.")
        return

    checklist = parse_checklist_text(str(checklist_text))
    st.session_state.pop(state_key, None)
    payload: dict[str, object] = {
        "contact_kind": contact_kind,
        "contact_id": contact_id_int,
        "title": str(task_title).strip() or title_default,
        "prompt": str(task_prompt).strip(),
        "checklist": checklist,
        "allow_tools": bool(allow_tools),
        "max_iterations": int(max_iterations),
    }
    if contact_kind == "agent":
        payload["agent_id"] = contact_id_int
        payload["participant_agent_ids"] = [contact_id_int] if contact_id_int is not None else []
    else:
        payload["participant_agent_ids"] = participant_agent_ids

    try:
        result = start_loop_task(**payload)
    except ApiError as error:
        st.error(f"Unable to start task: {error.detail}")
        st.session_state[state_key] = True
        return

    st.session_state["agent_loops_selected_contact_id"] = str(selected_contact.get("id") or "")
    started_task_id = str(result.get("task_id") or result.get("id") or "").strip()
    if started_task_id:
        st.session_state[f"agent_loops_selected_task_id:{selected_contact.get('id') or ''}"] = started_task_id
    st.success(f"Task started: {str(result.get('title') or payload['title'])}")
    st.rerun()


def _agent_loops_views_by_type(selected_module: dict[str, object]) -> dict[str, dict[str, object]]:
    views: dict[str, dict[str, object]] = {}
    for view in list(selected_module.get("views") or []):
        if not isinstance(view, dict):
            continue
        object_type = str((view.get("metadata") or {}).get("object_type") or "").strip().lower()
        if object_type:
            views[object_type] = view
    return views


def _filter_agent_loops_tasks(
    items: list[dict[str, object]],
    *,
    contact_kind: str,
    contact_id: object,
) -> list[dict[str, object]]:
    contact_key = f"{contact_kind}:{_safe_text(contact_id)}"
    filtered: list[dict[str, object]] = []
    for item in items:
        item_key = f"{str(item.get('contact_kind') or '').strip().lower()}:{_safe_text(item.get('contact_id'))}"
        if item_key == contact_key:
            filtered.append(item)
    return filtered


def _filter_agent_loops_files(items: list[dict[str, object]], *, root_path: str) -> list[dict[str, object]]:
    root_path = str(root_path or "").strip()
    if not root_path:
        return []
    return [item for item in items if str(item.get("path") or "").startswith(root_path)]


def _selected_contact_roots(contact_kind: str, contact_id: object) -> dict[str, str]:
    from apmatia.modules.agent_loops.state import resolve_contact_roots

    roots = resolve_contact_roots(contact_kind, _safe_text(contact_id))
    return {
        "workspace_root": str(roots.workspace_root),
        "knowledge_root": str(roots.knowledge_root),
        "task_root": str(roots.task_root),
    }


def _exit_agent_loops_shell() -> None:
    for key in (
        "agent_loops_selected_contact_id",
        "agent_loops_shell_sidebar_rendered",
        "selected_module_id",
        "selected_module_view_id",
    ):
        st.session_state.pop(key, None)
    st.session_state["selected_page"] = "discussion"


def _current_user_id() -> int | None:
    authenticated_user = st.session_state.get("authenticated_user")
    if not isinstance(authenticated_user, dict):
        return None
    try:
        user_id = authenticated_user.get("user_id")
        return None if user_id is None else int(user_id)
    except (TypeError, ValueError):
        return None


def _current_group_ids() -> set[int]:
    try:
        groups = list_groups()
    except ApiError:
        return set()
    group_ids: set[int] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        try:
            group_id = int(group.get("id"))
        except (TypeError, ValueError):
            continue
        group_ids.add(group_id)
    return group_ids


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _render_agent_loops_terminal_block(
    *,
    title: str,
    body: str,
    subtitle: str | None,
    language: str | None = None,
    prompt: str | None = None,
    status: str | None = None,
    body_height: str | int = "content",
) -> None:
    render_terminal_block(
        title,
        body or "",
        subtitle=subtitle,
        language=language,
        prompt=prompt,
        status=status,
        body_height=body_height,
    )


def _render_agent_loops_terminal_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] {
            background: #000000 !important;
        }
        section[data-testid="stSidebar"] {
            background: #000000 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_agent_loops_status_banner(*, status: str) -> None:
    normalized = str(status or "unknown").strip().lower()
    label_map = {
        "running": ("RUNNING", "#9dffad", "rgba(110, 255, 170, 0.18)"),
        "stopping": ("STOPPING", "#ffd86b", "rgba(255, 216, 107, 0.18)"),
        "stopped": ("STOPPED", "#ff9b9b", "rgba(255, 155, 155, 0.18)"),
        "failed": ("FAILED", "#ff7f7f", "rgba(255, 127, 127, 0.24)"),
        "completed": ("COMPLETED", "#9dffad", "rgba(110, 255, 170, 0.12)"),
        "queued": ("QUEUED", "#b5bcc7", "rgba(181, 188, 199, 0.12)"),
        "needs_review": ("NEEDS REVIEW", "#ffd86b", "rgba(255, 216, 107, 0.12)"),
    }
    label, color, background = label_map.get(
        normalized,
        (normalized.upper() or "UNKNOWN", "#b5bcc7", "rgba(181, 188, 199, 0.12)"),
    )
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            color: {color};
            background: {background};
            border: 1px solid {color};
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        ">{label}</div>
        """,
        unsafe_allow_html=True,
    )


def _safe_int(value: object, default: int | None = None) -> int | None:
    try:
        return default if value is None else int(value)
    except (TypeError, ValueError):
        return default


def _json_safe_payload(payload: object) -> object:
    if isinstance(payload, dict):
        return {str(key): _json_safe_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_json_safe_payload(value) for value in payload]
    if isinstance(payload, tuple):
        return [_json_safe_payload(value) for value in payload]
    if isinstance(payload, date) and not isinstance(payload, datetime):
        return payload.isoformat()
    if isinstance(payload, time):
        return payload.isoformat()
    if isinstance(payload, datetime):
        return payload.isoformat()
    return payload


def _agent_option_label(agent: object, agents: list[dict[str, object]] | None = None) -> str:
    if isinstance(agent, dict):
        return str(agent.get("name") or agent.get("username") or f"Agent {agent.get('id')}")
    if agents is None:
        return f"Agent {agent}"
    for agent in agents:
        if _safe_int(agent.get("id")) == _safe_int(agent):
            return str(agent.get("name") or agent.get("username") or f"Agent {agent}")
    return f"Agent {agent}"
