"""Tool management page for tool definitions, assignments, and safe execution."""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.interfaces.streamlit.api_client import (
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
        "help_text": (
            "Use this when you want a new agent object. The fields describe who owns the agent, "
            "what prompt it starts with, and which tools it can use."
        ),
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
        "help_text": "Use this when you want a copy of an existing agent without rebuilding the prompt surface from scratch.",
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
        "help_text": "Use this as a tiny smoke test or as the simplest possible tool shape.",
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
        "help_text": "Use this when an agent only needs a clock and should not mutate anything.",
    },
    "apmatia_create_tool": {
        "name": "apmatia_create_tool",
        "description": "Create a new tool definition for an existing provider.",
        "provider_id": "builtin.apmatia_create_tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "provider_id": {"type": "string"},
                "input_schema": {"type": "object"},
                "output_schema": {"type": ["object", "null"]},
                "enabled": {"type": "boolean"},
                "confirmation_required": {"type": "boolean"},
                "read_only": {"type": "boolean"},
                "metadata": {"type": "object"},
                "owner_user_id": {"type": "integer"},
                "owner_group_id": {"type": "integer"},
                "mode": {"type": "integer"},
            },
            "required": ["name", "provider_id", "input_schema"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"tool": {"type": "object"}},
            "required": ["tool"],
            "additionalProperties": True,
        },
        "arguments": {
            "name": "smoke_test_tool",
            "description": "Create a simple tool definition through Apmatia administration.",
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
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True},
        },
        "read_only": False,
        "help_text": (
            "Use this when you want a new tool definition to exist in Apmatia. "
            "The provider ID points at the implementation, while the JSON schema describes the contract."
        ),
    },
    "apmatia_system_audit": {
        "name": "apmatia_system_audit",
        "description": "Run a curated read-only system audit command from the approved allowlist.",
        "provider_id": "builtin.apmatia_system_audit",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": [
                        "apt",
                        "auditctl",
                        "blkid",
                        "cat",
                        "crontab",
                        "curl",
                        "dmesg",
                        "df",
                        "dpkg",
                        "du",
                        "ethtool",
                        "fail2ban-client",
                        "find",
                        "free",
                        "getenforce",
                        "grep",
                        "groups",
                        "head",
                        "hostname",
                        "id",
                        "ip",
                        "iptables",
                        "journalctl",
                        "last",
                        "lscpu",
                        "lsof",
                        "ls",
                        "lsblk",
                        "lspci",
                        "netstat",
                        "nmap",
                        "nstat",
                        "openssl",
                        "pgrep",
                        "ping",
                        "pip",
                        "ps",
                        "selinuxenabled",
                        "ss",
                        "ssl-cert-check",
                        "stat",
                        "systemctl",
                        "tail",
                        "tcpdump",
                        "top",
                        "ufw",
                        "uname",
                        "uptime",
                        "who",
                        "whoami",
                    ],
                },
                "args": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}},
                "returncode": {"type": "integer"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "truncated_stdout": {"type": "boolean"},
                "truncated_stderr": {"type": "boolean"},
            },
            "required": ["command", "args", "returncode", "stdout", "stderr", "truncated_stdout", "truncated_stderr"],
            "additionalProperties": False,
        },
        "arguments": {
            "command": "uname",
            "args": ["-a"],
        },
        "read_only": True,
        "help_text": (
            "Use this for safe host inspection. It can run only a curated allowlist of read-only commands and "
            "never invokes a shell, so it cannot chain arbitrary commands or use sudo."
        ),
    },
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


def _tool_group_label(tool: dict[str, Any]) -> str:
    provider_id = str(tool.get("provider_id") or "")
    if provider_id.startswith("builtin.apmatia_"):
        if provider_id.startswith("builtin.apmatia_system_"):
            return "System audit tools"
        return "Administration tools"
    if provider_id.startswith("builtin.memory_"):
        return "Memory tools"
    if provider_id.startswith("builtin.wiki_"):
        return "Wiki tools"
    return "Other tools"


def _tool_group_sort_key(tool: dict[str, Any]) -> tuple[str, str, int]:
    group_order = {
        "Administration tools": 0,
        "System audit tools": 1,
        "Memory tools": 2,
        "Wiki tools": 3,
        "Other tools": 4,
    }
    group = _tool_group_label(tool)
    return (
        str(group_order.get(group, 99)),
        str(tool.get("name") or ""),
        int(tool.get("id") or 0),
    )


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
        "output_schema": tool.get("output_schema") or {},
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
    st.info(
        "A tool definition is the recipe Apmatia uses to turn a provider into something an agent can call. "
        "Start with a template, keep the advanced JSON mostly untouched unless you are changing the contract, "
        "and use the assignment section to decide who gets access."
    )

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
                grouped_tools: dict[str, list[dict[str, Any]]] = {}
                for tool in sorted(tools, key=_tool_group_sort_key):
                    grouped_tools.setdefault(_tool_group_label(tool), []).append(tool)

                selected_tool_ids: list[int] = []
                for group_name, grouped_items in grouped_tools.items():
                    with st.container(border=True):
                        st.write(f"**{group_name}**")
                        st.caption("Select one or more tools to grant in a single step.")
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
                for tool in available_tools:
                    st.caption(
                        f"{tool.get('name')} (ID {tool.get('id')}) · "
                        f"{tool.get('provider_id')} · "
                        f"{'confirmation required' if tool.get('confirmation_required') else 'no confirmation'}"
                    )

    st.divider()
    st.subheader("Edit tool definition" if is_editing else "Tool definition")
    st.caption(
        "This form has two layers: the plain-English fields near the top and the advanced JSON contract below. "
        "If you are not changing the implementation shape, you probably only need the top section."
    )
    st.info(template.get("help_text", template["description"]))
    with st.form("apmatia_tool_definition_form"):
        left, right = st.columns(2)
        with left:
            name = st.text_input(
                "Name",
                value=str(form_defaults["name"]),
                help="The unique human-readable name for this tool. Keep it short and memorable.",
            )
            description = st.text_area(
                "Description",
                value=str(form_defaults["description"]),
                height=110,
                help="Explain what the tool does in plain language so future you and your agents can recognize it quickly.",
            )
            provider_id = st.text_input(
                "Provider ID",
                value=str(form_defaults["provider_id"]),
                help="The implementation that actually runs when this tool is called. This usually points at a builtin or plugin provider.",
            )
        with right:
            enabled = st.checkbox(
                "Enabled",
                value=bool(form_defaults["enabled"]),
                help="Turn this off if you want to keep the definition around without letting agents use it.",
            )
            confirmation_required = st.checkbox(
                "Confirmation required",
                value=bool(form_defaults["confirmation_required"]),
                help="Require an approval step before the tool can run. Good for risky or irreversible actions.",
            )
            read_only = st.checkbox(
                "Read only",
                value=bool(form_defaults["read_only"]),
                help="Mark this if the tool should not change state. Read-only tools are safer and easier to reason about.",
            )

        with st.expander("Advanced schema and metadata", expanded=False):
            st.caption(
                "This section describes the contract between the tool caller and the provider. "
                "If you are just exploring, you can leave these values as the template filled them in."
            )
            metadata = st.text_area(
                "Metadata (JSON object)",
                value=_json_text(form_defaults["metadata"]),
                height=110,
                help="Free-form notes for humans and automation. It does not affect execution logic.",
            )
            input_schema = st.text_area(
                "Input schema (JSON object)",
                value=_json_text(form_defaults["input_schema"]),
                height=180,
                help="Describe the arguments the tool accepts. This is the part agents use to know what to send.",
            )
            output_schema = st.text_area(
                "Output schema (JSON object, optional)",
                value=_json_text(form_defaults["output_schema"]),
                height=180,
                help="Describe what the tool returns. Leave it as {} if you do not need to be precise here.",
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
        selected_execution_tool = st.selectbox(
            "Available tool",
            options=available_tools,
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
