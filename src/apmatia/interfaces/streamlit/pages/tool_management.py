"""Tool management page for tool definitions, assignments, and safe execution."""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    assign_tool_to_agent,
    create_tool_definition,
    execute_tool_call,
    list_agent_tool_assignments,
    list_agents,
    list_tool_definitions,
    list_tools_available_to_agent,
    unassign_tool_from_agent,
    update_tool_definition,
)


_TOOL_TEMPLATES = {
    "apmatia_create_agent": {
        "name": "apmatia_create_agent",
        "description": "Create a new Apmatia agent with the full prompt surface.",
        "provider_id": "builtin.apmatia_create_agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "owner_user_id": {"type": "integer"},
                "owner_group_id": {"type": "integer"},
                "mode": {"type": "integer"},
                "system_prompt_id": {"type": "integer"},
                "memory_id": {"type": "integer"},
                "rag_root_ids": {"type": "array", "items": {"type": "integer"}},
                "tool_ids": {"type": "array", "items": {"type": "integer"}},
                "default_model_id": {"type": "integer"},
                "active_model_id": {"type": "integer"},
                "metadata": {"type": "object"},
                "personality": {"type": "string"},
                "skills": {"type": "string"},
                "purpose": {"type": "string"},
                "backstory": {"type": "string"},
                "communication_style": {"type": "string"},
                "operating_principles": {"type": "string"},
                "autonomy_level": {"type": "string"},
                "decision_making_style": {"type": "string"},
                "memory_policy": {"type": "string"},
                "domain_priorities": {"type": "string"},
                "relationship_to_user": {"type": "string"},
                "tool_use_policy": {"type": "string"},
                "capability_boundaries": {"type": "string"},
                "output_preferences": {"type": "string"},
                "safety_ethics": {"type": "string"},
                "selfhood_truthfulness": {"type": "string"},
                "conflict_resolution_rules": {"type": "string"},
                "use_raw_prompt_override": {"type": "boolean"},
                "raw_prompt_override": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"agent": {"type": "object"}},
            "required": ["agent"],
            "additionalProperties": True,
        },
        "arguments": {
            "name": "Welcome to Apmatia",
            "purpose": "Help the user build and organize things within Apmatia.",
            "personality": "Warm, practical, and encouraging.",
            "skills": "Agent design, prompt shaping, and Apmatia administration.",
        },
        "read_only": False,
    },
    "clone_agent_as": {
        "name": "clone_agent_as",
        "description": "Clone an existing Apmatia agent into a new agent name.",
        "provider_id": "builtin.apmatia_clone_agent_as",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_agent_id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "required": ["source_agent_id", "name"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"agent": {"type": "object"}},
            "required": ["agent"],
            "additionalProperties": True,
        },
        "arguments": {
            "source_agent_id": 1,
            "name": "Clone of existing agent",
        },
        "read_only": False,
    },
    "echo": {
        "name": "echo",
        "description": "Return the provided text without modification.",
        "provider_id": "builtin.echo",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "arguments": {"text": "Hello from Apmatia"},
        "read_only": True,
    },
    "get_current_time": {
        "name": "get_current_time",
        "description": "Return the current UTC timestamp.",
        "provider_id": "builtin.get_current_time",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"current_time": {"type": "string"}},
            "required": ["current_time"],
            "additionalProperties": False,
        },
        "arguments": {},
        "read_only": True,
    },
}

_GROUP_ORDER = {
    "Apmatia administration": 0,
    "Integrated productivity environment": 1,
    "System audit": 2,
    "Memory management": 3,
    "Agent config": 4,
    "Dev tools": 5,
    "Wiki management": 6,
    "Tool management": 7,
    "Workspace modules": 8,
    "Agent loops": 9,
}

_SOURCE_LABELS = {
    "apmatia_administration": "Apmatia administration",
    "ipe": "Integrated productivity environment",
    "system_audit": "System audit",
    "memory_management": "Memory management",
    "agent_config": "Agent config",
    "dev_tools": "Dev tools",
    "wiki_management": "Wiki management",
    "tool_management": "Tool management",
    "workspace_modules": "Workspace modules",
    "agent_loops": "Agent loops",
}

_PROVIDER_GROUP_FALLBACKS: dict[str, tuple[str, str, str]] = {
    "builtin.apmatia_create_agent": ("library", "apmatia_administration", "Apmatia administration"),
    "builtin.apmatia_clone_agent_as": ("library", "apmatia_administration", "Apmatia administration"),
    "builtin.apmatia_set_agent_mode": ("library", "apmatia_administration", "Apmatia administration"),
    "builtin.apmatia_system_audit": ("library", "system_audit", "System audit"),
    "builtin.ipe_what_do_i_do": ("library", "ipe", "Integrated productivity environment"),
    "builtin.memory_create": ("library", "memory_management", "Memory management"),
    "builtin.memory_search": ("library", "memory_management", "Memory management"),
    "builtin.memory_get": ("library", "memory_management", "Memory management"),
    "builtin.memory_update": ("library", "memory_management", "Memory management"),
    "builtin.memory_archive": ("library", "memory_management", "Memory management"),
    "builtin.agent_config_readme_first": ("module", "agent_config", "Agent config"),
    "builtin.agent_config_tree": ("module", "agent_config", "Agent config"),
    "builtin.agent_config_read": ("module", "agent_config", "Agent config"),
    "builtin.apmatia_tree": ("library", "dev_tools", "Dev tools"),
    "builtin.apmatia_read": ("library", "dev_tools", "Dev tools"),
    "builtin.apmatia_trace_import": ("library", "dev_tools", "Dev tools"),
    "builtin.wiki_create_branch": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_create_leaf": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_update_node": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_get_tree": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_search": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_move_node": ("library", "wiki_management", "Wiki management"),
    "builtin.wiki_reorder_node": ("library", "wiki_management", "Wiki management"),
    "builtin.plan_workspace_module": ("library", "tool_management", "Tool management"),
    "builtin.create_workspace_module": ("library", "tool_management", "Tool management"),
    "builtin.list_workspace_module_files": ("library", "tool_management", "Tool management"),
    "builtin.read_workspace_module_file": ("library", "tool_management", "Tool management"),
    "builtin.write_workspace_module_file": ("library", "tool_management", "Tool management"),
    "builtin.validate_workspace_module": ("library", "tool_management", "Tool management"),
    "builtin.agent_loops_list_agents": ("module", "agent_loops", "Agent loops"),
    "builtin.echo": ("library", "tool_management", "Tool management"),
    "builtin.get_current_time": ("library", "tool_management", "Tool management"),
}


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _parse_json_field(raw_value: str, fallback: object) -> object:
    text = raw_value.strip()
    if not text:
        return fallback
    return json.loads(text)


def _tool_label(tool: dict[str, Any]) -> str:
    tool_id = tool.get("id")
    name = tool.get("name") or "Unnamed tool"
    provider_id = tool.get("provider_id") or "unknown"
    return f"{name} (ID {tool_id}, {provider_id})"


def _tool_source(tool: dict[str, Any]) -> tuple[str, str, str]:
    metadata = tool.get("metadata")
    if isinstance(metadata, dict):
        for key in ("library", "module"):
            source = str(metadata.get(key) or "").strip()
            if source:
                return key, source, _SOURCE_LABELS.get(source, _humanize_source_name(source))

    provider_id = str(tool.get("provider_id") or "").strip()
    if provider_id in _PROVIDER_GROUP_FALLBACKS:
        return _PROVIDER_GROUP_FALLBACKS[provider_id]
    return ("library", "other", "Other tools")


def _humanize_source_name(source: str) -> str:
    normalized = source.replace("-", "_").strip("_")
    if not normalized:
        return "Other tools"
    parts = [part for part in normalized.split("_") if part]
    pretty = " ".join(parts)
    return pretty[:1].upper() + pretty[1:] if pretty else "Other tools"


def _tool_group_label(tool: dict[str, Any]) -> str:
    _, _, label = _tool_source(tool)
    return label


def _tool_group_caption(tool: dict[str, Any]) -> str:
    kind, source_id, label = _tool_source(tool)
    if label == "Other tools":
        return "Source unavailable"
    return f"{kind} `{source_id}`"


def _tool_group_sort_key(tool: dict[str, Any]) -> tuple[str, str, int]:
    group = _tool_group_label(tool)
    return (
        str(_GROUP_ORDER.get(group, 99)),
        str(tool.get("name") or ""),
        int(tool.get("id") or 0),
    )


def _group_tools(tools: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped_tools: dict[str, list[dict[str, Any]]] = {}
    for tool in sorted(tools, key=_tool_group_sort_key):
        grouped_tools.setdefault(_tool_group_label(tool), []).append(tool)
    return grouped_tools


def _agent_label(agent: dict[str, Any]) -> str:
    agent_id = agent.get("id")
    name = agent.get("name") or "Unnamed agent"
    return f"{name} (ID {agent_id})"


def _optional_override_choice(value: bool | None) -> str:
    if value is None:
        return "inherit"
    return "true" if value else "false"


def _optional_override_value(choice: str) -> bool | None:
    if choice == "true":
        return True
    if choice == "false":
        return False
    return None


def _matching_tool(tools: list[dict[str, Any]], tool_id: object) -> dict[str, Any] | None:
    for tool in tools:
        if tool.get("id") == tool_id:
            return tool
    return None


def _tool_form_defaults(tool: dict[str, Any] | None, template: dict[str, Any]) -> dict[str, Any]:
    if tool is None:
        return {
            "id": None,
            "name": template["name"],
            "description": template["description"],
            "provider_id": template["provider_id"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": bool(template["read_only"]),
            "metadata": {"builtin": True},
            "input_schema": template["input_schema"],
            "output_schema": template["output_schema"],
        }
    return {
        "id": tool.get("id"),
        "name": tool.get("name", ""),
        "description": tool.get("description", ""),
        "provider_id": tool.get("provider_id", ""),
        "enabled": bool(tool.get("enabled", True)),
        "confirmation_required": bool(tool.get("confirmation_required", False)),
        "read_only": bool(tool.get("read_only", True)),
        "metadata": tool.get("metadata", {}),
        "input_schema": tool.get("input_schema", {}),
        "output_schema": tool.get("output_schema"),
    }


def render() -> None:
    try:
        agents = list_agents()
        tools = list_tool_definitions()
    except ApiError as error:
        st.error(f"Unable to load tool data: {error.detail}")
        return

    st.title("Tool Management")
    st.caption("Create tool definitions, grant them to agents, and run safe demo calls through the local API.")

    if "tool_template_name" not in st.session_state:
        st.session_state["tool_template_name"] = "echo"
    if "tool_execution_result" not in st.session_state:
        st.session_state["tool_execution_result"] = None
    if "tool_editing_id" not in st.session_state:
        st.session_state["tool_editing_id"] = None

    template_name = st.selectbox(
        "Tool template",
        options=list(_TOOL_TEMPLATES.keys()),
        index=list(_TOOL_TEMPLATES.keys()).index(st.session_state["tool_template_name"]),
    )
    st.session_state["tool_template_name"] = template_name
    template = _TOOL_TEMPLATES[template_name]
    editing_tool = _matching_tool(tools, st.session_state.get("tool_editing_id"))
    form_defaults = _tool_form_defaults(editing_tool, template)
    is_editing = editing_tool is not None
    assignments: list[dict[str, Any]] = []
    available_tools: list[dict[str, Any]] = []
    agent_id: int | None = None

    st.subheader("Agent access")
    if not agents:
        st.info("Create an agent first so tools can be assigned.")
    else:
        selected_agent = st.selectbox(
            "Agent",
            options=agents,
            format_func=_agent_label,
            key="tool_management_agent_select",
        )
        agent_id = int(selected_agent.get("id"))

        try:
            assignments = list_agent_tool_assignments(agent_id)
            available_tools = list_tools_available_to_agent(agent_id)
        except ApiError as error:
            st.error(f"Unable to load agent tool access: {error.detail}")
            return

        if not tools:
            st.info("Create at least one tool definition before assigning tools to agents.")
        else:
            with st.form("apmatia_tool_assignment_form"):
                st.write("Select the tools to grant to this agent.")
                assigned_tool_ids = {
                    int(assignment.get("tool_id"))
                    for assignment in assignments
                    if assignment.get("tool_id") is not None
                }
                grouped_tools = _group_tools(tools)

                selected_tool_ids: list[int] = []
                for group_name, grouped_items in grouped_tools.items():
                    with st.container(border=True):
                        st.write(f"**{group_name}**")
                        st.caption(f"Select one or more tools from {_tool_group_caption(grouped_items[0])}.")
                        for tool in grouped_items:
                            tool_id = int(tool.get("id"))
                            selected = st.checkbox(
                                _tool_label(tool),
                                value=tool_id in assigned_tool_ids,
                                key=f"tool_management_assign_tool_{agent_id}_{tool_id}",
                            )
                            if selected:
                                selected_tool_ids.append(tool_id)

                assign_cols = st.columns(3)
                with assign_cols[0]:
                    assignment_enabled = st.checkbox("Assignment enabled", value=True)
                with assign_cols[1]:
                    confirmation_override = st.selectbox(
                        "Confirmation override",
                        options=["inherit", "true", "false"],
                        index=0,
                    )
                with assign_cols[2]:
                    read_only_override = st.selectbox(
                        "Read-only override",
                        options=["inherit", "true", "false"],
                        index=0,
                    )
                assign_submitted = st.form_submit_button("Grant selected tools to agent")

            if assign_submitted:
                if not selected_tool_ids:
                    st.info("Select at least one tool to grant.")
                else:
                    granted_tool_ids: list[int] = []
                    already_assigned_tool_ids = set(assigned_tool_ids)
                    try:
                        for tool_id in selected_tool_ids:
                            if tool_id in already_assigned_tool_ids:
                                continue
                            assignment = assign_tool_to_agent(
                                agent_id,
                                tool_id,
                                enabled=assignment_enabled,
                                confirmation_required=_optional_override_value(confirmation_override),
                                read_only=_optional_override_value(read_only_override),
                            )
                            granted_tool_ids.append(int(assignment.get("tool_id")))
                    except ApiError as error:
                        st.error(f"Unable to grant tool: {error.detail}")
                    else:
                        if granted_tool_ids:
                            st.success(
                                f"Granted {len(granted_tool_ids)} tool(s) to agent {agent_id}: "
                                + ", ".join(str(tool_id) for tool_id in granted_tool_ids)
                                + "."
                            )
                        else:
                            st.info("All selected tools were already assigned.")
                        st.rerun()

            st.write("**Assigned tool mappings**")
            if not assignments:
                st.info("This agent has no explicit tool assignments yet.")
            else:
                for assignment in assignments:
                    tool = _matching_tool(tools, assignment.get("tool_id"))
                    label = tool.get("name") if tool else f"Tool {assignment.get('tool_id')}"
                    with st.container(border=True):
                        st.write(f"**{label}**")
                        st.caption(
                            f"Tool ID {assignment.get('tool_id')} · "
                            f"{'enabled' if assignment.get('enabled', True) else 'disabled'} · "
                            f"confirmation={_optional_override_choice(assignment.get('confirmation_required'))} · "
                            f"read_only={_optional_override_choice(assignment.get('read_only'))}"
                        )
                        if st.button(
                            "Unassign",
                            key=f"unassign_tool_{agent_id}_{assignment.get('tool_id')}",
                        ):
                            try:
                                unassign_tool_from_agent(agent_id, int(assignment.get("tool_id")))
                            except ApiError as error:
                                st.error(f"Unable to unassign tool: {error.detail}")
                            else:
                                st.success("Tool unassigned.")
                                st.rerun()

            st.write("**Currently available to this agent**")
            if not available_tools:
                st.info("No enabled tools are currently available to this agent.")
            else:
                for group_name, grouped_items in _group_tools(available_tools).items():
                    with st.container(border=True):
                        st.write(f"**{group_name}**")
                        st.caption(f"Source: {_tool_group_caption(grouped_items[0])}.")
                        for tool in grouped_items:
                            st.caption(
                                f"{tool.get('name')} (ID {tool.get('id')}) · "
                                f"{tool.get('provider_id')} · "
                                f"{'confirmation required' if tool.get('confirmation_required') else 'no confirmation'}"
                            )

    st.divider()
    st.subheader("Edit tool definition" if is_editing else "Tool definition")
    with st.form("apmatia_tool_definition_form"):
        left, right = st.columns(2)
        with left:
            name = st.text_input("Name", value=str(form_defaults["name"]))
            description = st.text_area("Description", value=str(form_defaults["description"]), height=110)
            provider_id = st.text_input("Provider ID", value=str(form_defaults["provider_id"]))
        with right:
            enabled = st.checkbox("Enabled", value=bool(form_defaults["enabled"]))
            confirmation_required = st.checkbox("Confirmation required", value=bool(form_defaults["confirmation_required"]))
            read_only = st.checkbox("Read only", value=bool(form_defaults["read_only"]))
            metadata = st.text_area("Metadata (JSON object)", value=_json_text(form_defaults["metadata"]), height=110)

        input_schema = st.text_area(
            "Input schema (JSON object)",
            value=_json_text(form_defaults["input_schema"]),
            height=180,
        )
        output_schema = st.text_area(
            "Output schema (JSON object, optional)",
            value=_json_text(form_defaults["output_schema"]),
            height=180,
        )
        save_submitted = st.form_submit_button("Save changes" if is_editing else "Create tool definition")
        cancel_submitted = st.form_submit_button("Cancel edit") if is_editing else False

    if cancel_submitted:
        st.session_state["tool_editing_id"] = None
        st.rerun()

    if save_submitted:
        try:
            payload = {
                "name": name,
                "description": description,
                "provider_id": provider_id,
                "input_schema": _parse_json_field(input_schema, {}),
                "output_schema": _parse_json_field(output_schema, {}),
                "enabled": enabled,
                "confirmation_required": confirmation_required,
                "read_only": read_only,
                "metadata": _parse_json_field(metadata, {}),
            }
            saved = (
                update_tool_definition(int(editing_tool.get("id")), **payload)
                if is_editing
                else create_tool_definition(**payload)
            )
        except (ApiError, TypeError, ValueError, json.JSONDecodeError) as error:
            detail = error.detail if isinstance(error, ApiError) else str(error)
            st.error(f"Unable to save tool definition: {detail}")
        else:
            st.session_state["tool_editing_id"] = None
            action = "Updated" if is_editing else "Created"
            st.success(f"{action} tool definition {saved.get('name')} (ID {saved.get('id')}).")
            st.rerun()

    st.divider()
    st.subheader("Existing tool definitions")
    if not tools:
        st.info("No tool definitions are available yet.")
    else:
        for tool in tools:
            with st.container(border=True):
                st.write(f"**{tool.get('name') or 'Unnamed tool'}**")
                st.caption(
                    f"ID {tool.get('id')} · {tool.get('provider_id')} · "
                    f"{'enabled' if tool.get('enabled', True) else 'disabled'} · "
                    f"{'read-only' if tool.get('read_only', True) else 'mutable'}"
                )
                st.write(tool.get("description") or "No description provided.")
                if st.button("Edit", key=f"edit_tool_{tool.get('id')}"):
                    st.session_state["tool_editing_id"] = tool.get("id")
                    st.rerun()

    st.divider()
    st.subheader("Execute tool")
    if not agents:
        st.info("Create an agent first so tools can be assigned and executed.")
    elif not available_tools or agent_id is None:
        st.info("Grant at least one enabled tool to run a manual tool call.")
    else:
        grouped_execution_tools = _group_tools(available_tools)
        selected_tool_group = st.selectbox(
            "Tool group",
            options=list(grouped_execution_tools.keys()),
            key="tool_management_execute_tool_group_select",
        )
        selected_execution_tool = st.selectbox(
            "Available tool",
            options=grouped_execution_tools[selected_tool_group],
            format_func=_tool_label,
            key="tool_management_execute_tool_select",
        )
        selected_template = next(
            (
                item
                for item in _TOOL_TEMPLATES.values()
                if item["provider_id"] == selected_execution_tool.get("provider_id")
            ),
            {"arguments": {}},
        )

        with st.form("apmatia_tool_execute_form"):
            arguments = st.text_area(
                "Arguments (JSON object)",
                value=_json_text(selected_template.get("arguments", {})),
                height=140,
            )
            discussion_id = st.text_input("Discussion ID (optional)", value="")
            approval_granted = st.checkbox("Approval already granted", value=False)
            execute_submitted = st.form_submit_button("Execute tool call")

        if execute_submitted:
            try:
                result = execute_tool_call(
                    int(selected_execution_tool.get("id")),
                    requester_agent_id=agent_id,
                    arguments=_parse_json_field(arguments, {}),
                    discussion_id=discussion_id.strip() or None,
                    approval_granted=approval_granted,
                )
            except (ApiError, TypeError, ValueError, json.JSONDecodeError) as error:
                detail = error.detail if isinstance(error, ApiError) else str(error)
                st.error(f"Unable to execute tool: {detail}")
            else:
                st.session_state["tool_execution_result"] = result
                st.success(f"Tool call finished with status: {result.get('status')}.")

    tool_execution_result = st.session_state.get("tool_execution_result")
    if tool_execution_result:
        st.write("**Last tool result**")
        st.code(_json_text(tool_execution_result), language="json")
