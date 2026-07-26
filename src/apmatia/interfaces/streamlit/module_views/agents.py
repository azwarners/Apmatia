"""Schema-selected Streamlit renderer for the stable agents module view."""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_agent_prompt,
    execute_module_command,
    get_agent_prompt,
    get_compiled_agent_prompt,
    list_llm_configs,
    update_agent_prompt,
)


COMMAND_PREFIX = "agents"


def _empty_form_values() -> dict[str, object]:
    return {
        "id": None,
        "name": "",
        "owner_user_id": None,
        "owner_group_id": None,
        "prompt_id": None,
        "memory_id": 0,
        "rag_root_ids": [],
        "tool_ids": [],
        "default_model_id": None,
        "active_model_id": None,
        "workspace_root": "",
        "knowledge_root": "",
        "metadata": {},
        "personality": "Helpful, calm, and thoughtful.",
        "skills": "General assistance, analysis, and coordination.",
        "purpose": "Support the user with reliable and focused help.",
        "backstory": "An AI assistant built to work clearly and carefully.",
        "communication_style": "Clear, concise, and friendly.",
        "operating_principles": "Be accurate, practical, and easy to work with.",
        "autonomy_level": "Act with moderate autonomy and ask when uncertain.",
        "decision_making_style": "Prefer simple, reversible decisions with explicit reasoning.",
        "memory_policy": "Use only available context and avoid assuming hidden memory.",
        "domain_priorities": "Prioritize the user's immediate task and relevant context.",
        "relationship_to_user": "A collaborative assistant working alongside the user.",
        "tool_use_policy": "Use tools only when they clearly help accomplish the task.",
        "capability_boundaries": "Be honest about limits and avoid claiming unavailable abilities.",
        "output_preferences": "Prefer structured, actionable, and readable responses.",
        "safety_ethics": "Avoid harmful actions, respect consent, and follow safety rules.",
        "selfhood_truthfulness": "Do not pretend to be human or claim subjective experience.",
        "conflict_resolution_rules": "Resolve ambiguity by asking concise clarifying questions.",
        "use_raw_prompt_override": False,
        "raw_prompt_override": "",
    }


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _parse_json_field(raw_value: str, fallback: object) -> object:
    text = raw_value.strip()
    if not text:
        return fallback
    return json.loads(text)


def _model_option_label(config: dict[str, object]) -> str:
    config_id = config.get("id")
    name = config.get("user_alias") or config.get("name") or "Unnamed config"
    provider_name = config.get("provider_name") or config.get("model_name") or "default"
    seats = config.get("seats")
    if seats is not None and seats > 1:
        return f"{name} (ID {config_id}, {provider_name}, {seats} seats)"
    return f"{name} (ID {config_id}, {provider_name})"


def _model_option_index(configs: list[dict[str, object]], selected_id: object) -> int:
    if selected_id is None:
        return 0
    for index, config in enumerate(configs, start=1):
        if config.get("id") == selected_id:
            return index
    return 0


def _build_prompt_preview(
    *,
    name: str,
    personality: str,
    skills: str,
    purpose: str,
    backstory: str,
    communication_style: str,
    operating_principles: str,
    autonomy_level: str,
    decision_making_style: str,
    memory_policy: str,
    domain_priorities: str,
    relationship_to_user: str,
    tool_use_policy: str,
    capability_boundaries: str,
    output_preferences: str,
    safety_ethics: str,
    selfhood_truthfulness: str,
    conflict_resolution_rules: str,
    use_raw_prompt_override: bool,
    raw_prompt_override: str,
) -> str:
    if use_raw_prompt_override and raw_prompt_override.strip():
        return raw_prompt_override.strip()
    return (
        f"You are {name.strip() or 'an AI assistant'}.\n\n"
        f"You are an AI system, not a human.\n\n"
        f"Purpose: {purpose.strip()}\n\n"
        f"Personality: {personality.strip()}\n\n"
        f"Skills: {skills.strip()}\n\n"
        f"Backstory: {backstory.strip()}\n\n"
        f"Relationship to user: {relationship_to_user.strip()}\n\n"
        f"Communication style: {communication_style.strip()}\n\n"
        f"Operating principles: {operating_principles.strip()}\n\n"
        f"Autonomy: {autonomy_level.strip()}\n\n"
        f"Decision making: {decision_making_style.strip()}\n\n"
        f"Memory policy: {memory_policy.strip()}\n\n"
        f"Tool policy: {tool_use_policy.strip()}\n\n"
        f"Capability boundaries: {capability_boundaries.strip()}\n\n"
        f"Domain priorities: {domain_priorities.strip()}\n\n"
        f"Safety and ethics: {safety_ethics.strip()}\n\n"
        f"Truthfulness: {selfhood_truthfulness.strip()}\n\n"
        f"Conflict resolution: {conflict_resolution_rules.strip()}\n\n"
        f"Output preferences: {output_preferences.strip()}"
    ).strip()


def _agent_label(agent: dict[str, object]) -> str:
    agent_id = agent.get("id")
    name = agent.get("name") or "Unnamed agent"
    return f"{name} (ID {agent_id})"


def _selected_index(agents: list[dict[str, object]], selected_id: object) -> int:
    if selected_id is None:
        return 0
    for index, agent in enumerate(agents):
        if agent.get("id") == selected_id:
            return index
    return 0


def _authenticated_user_id() -> int | None:
    authenticated_user = st.session_state.get("authenticated_user")
    if not isinstance(authenticated_user, dict):
        return None
    try:
        user_id = authenticated_user.get("user_id")
        return None if user_id is None else int(user_id)
    except (TypeError, ValueError):
        return None


def _visible_agent(agent: dict[str, object], current_user_id: int | None, visible_group_ids: set[int]) -> bool:
    if current_user_id is None:
        return True
    try:
        owner_user_id = agent.get("owner_user_id")
        owner_group_id = agent.get("owner_group_id")
    except AttributeError:
        return False
    if owner_user_id == current_user_id:
        return True
    if owner_group_id is not None and owner_group_id in visible_group_ids:
        return True
    return False


def _merge_agent_and_prompt(agent: dict[str, object], prompt_values: dict[str, object]) -> dict[str, object]:
    merged = {**_empty_form_values(), **dict(agent)}
    for key, value in prompt_values.items():
        if key != "id":
            merged[key] = value
    return merged


def _delete_confirmation_target() -> dict[str, object] | None:
    target = st.session_state.get("agent_delete_target")
    return target if isinstance(target, dict) else None


def render(items: Iterable[dict[str, object]]) -> None:
    agents = [dict(item) for item in items if isinstance(item, dict)]
    try:
        model_configs = list_llm_configs()
    except ApiError as error:
        st.error(f"Unable to load agent data: {error.detail}")
        return

    st.title("Agents")
    st.caption("Create, edit, clone, and remove agents through the stable agents module API.")

    model_options = [{"id": None, "user_alias": "None", "provider_name": ""}] + model_configs
    visible_agents = agents

    if "agent_selected_id" not in st.session_state:
        st.session_state["agent_selected_id"] = visible_agents[0].get("id") if visible_agents else None
    if "agent_form_values" not in st.session_state:
        st.session_state["agent_form_values"] = _empty_form_values()

    selected_agent_id = st.session_state["agent_selected_id"]
    if visible_agents and selected_agent_id not in {agent.get("id") for agent in visible_agents}:
        selected_agent_id = visible_agents[0].get("id")
        st.session_state["agent_selected_id"] = selected_agent_id

    st.subheader("Agents")
    if not visible_agents:
        st.info("No agents have been created yet.")
    else:
        selected_agent = st.selectbox(
            "Select an agent",
            options=visible_agents,
            index=_selected_index(visible_agents, selected_agent_id),
            format_func=_agent_label,
        )
        selected_agent_id = selected_agent.get("id")
        st.session_state["agent_selected_id"] = selected_agent_id

    if selected_agent_id is not None:
        selected_agent = next((agent for agent in visible_agents if agent.get("id") == selected_agent_id), None)
    else:
        selected_agent = None

    delete_target = _delete_confirmation_target()
    if delete_target is not None:
        if selected_agent is None or delete_target.get("id") != selected_agent.get("id"):
            st.session_state.pop("agent_delete_target", None)
            delete_target = None

    if selected_agent is not None:
        st.subheader("Selected agent")
        st.write(f"**{selected_agent.get('name') or 'Unnamed agent'}**")
        st.caption(
            "ID {id} · owner user {owner_user_id} · owner group {owner_group_id} · prompt {prompt_id} · memory {memory_id}".format(
                id=selected_agent.get("id"),
                owner_user_id=selected_agent.get("owner_user_id"),
                owner_group_id=selected_agent.get("owner_group_id"),
                prompt_id=selected_agent.get("prompt_id"),
                memory_id=selected_agent.get("memory_id"),
            )
        )
        default_model = {config.get("id"): config for config in model_configs}.get(selected_agent.get("default_model_id"))
        active_model = {config.get("id"): config for config in model_configs}.get(selected_agent.get("active_model_id"))
        st.caption(
            "Default model: {default_model} · Active model: {active_model}".format(
                default_model=(
                    (default_model.get("user_alias") or default_model.get("name"))
                    if default_model
                    else "None"
                ),
                active_model=(
                    (active_model.get("user_alias") or active_model.get("name"))
                    if active_model
                    else "None"
                ),
            )
        )
        st.json(
            {
                "rag_root_ids": selected_agent.get("rag_root_ids", []),
                "tool_ids": selected_agent.get("tool_ids", []),
                "workspace_root": selected_agent.get("workspace_root", ""),
                "knowledge_root": selected_agent.get("knowledge_root", ""),
                "metadata": selected_agent.get("metadata", {}),
            }
        )
        if selected_agent.get("prompt_id"):
            try:
                preview = get_compiled_agent_prompt(
                    int(selected_agent.get("prompt_id")),
                    name=str(selected_agent.get("name") or "Agent"),
                )
                st.caption("Compiled prompt preview:")
                st.code(preview, language="text")
            except ApiError:
                pass
        action_col, clone_col, delete_col = st.columns(3)
        with action_col:
            if st.button("Edit selected agent", key=f"edit_agent_{selected_agent.get('id')}"):
                prompt_values = {}
                prompt_id = selected_agent.get("prompt_id")
                if prompt_id:
                    try:
                        prompt_values = get_agent_prompt(int(prompt_id)) or {}
                    except ApiError:
                        prompt_values = {}
                st.session_state["agent_form_values"] = _merge_agent_and_prompt(selected_agent, dict(prompt_values))
                st.rerun()
        with clone_col:
            if st.button("Clone selected agent", key=f"clone_agent_{selected_agent.get('id')}"):
                prompt_values = {}
                prompt_id = selected_agent.get("prompt_id")
                if prompt_id:
                    try:
                        prompt_values = get_agent_prompt(int(prompt_id)) or {}
                    except ApiError:
                        prompt_values = {}
                cloned_form_values = _merge_agent_and_prompt(selected_agent, dict(prompt_values))
                cloned_form_values["id"] = None
                cloned_form_values["prompt_id"] = None
                cloned_form_values["name"] = f"Copy of {selected_agent.get('name') or 'Agent'}"
                st.session_state["agent_form_values"] = cloned_form_values
                st.rerun()
        with delete_col:
            if delete_target is not None and delete_target.get("id") == selected_agent.get("id"):
                st.warning("Delete this agent?")
                cancel_col, confirm_col, _ = st.columns([1, 1, 8])
                with cancel_col:
                    if st.button("Cancel", key=f"cancel_delete_agent_{selected_agent.get('id')}", width="content"):
                        st.session_state.pop("agent_delete_target", None)
                        st.rerun()
                with confirm_col:
                    if st.button("Delete", key=f"confirm_delete_agent_{selected_agent.get('id')}", width="content", type="primary"):
                        try:
                            execute_module_command(
                                f"{COMMAND_PREFIX}.delete",
                                item_id=int(selected_agent.get("id")),
                            )
                        except ApiError as error:
                            st.error(f"Unable to delete agent: {error.detail}")
                        else:
                            if st.session_state.get("agent_form_values", {}).get("id") == selected_agent.get("id"):
                                st.session_state["agent_form_values"] = _empty_form_values()
                            st.session_state.pop("agent_delete_target", None)
                            st.session_state["agent_selected_id"] = None
                            st.success("Agent deleted.")
                            st.rerun()
            elif st.button("Delete selected agent", key=f"delete_agent_{selected_agent.get('id')}"):
                st.session_state["agent_delete_target"] = {
                    "id": selected_agent.get("id"),
                    "name": selected_agent.get("name") or "Agent",
                }
                st.rerun()

    st.divider()
    st.subheader("Agent editor")
    form_values = {**_empty_form_values(), **st.session_state["agent_form_values"]}
    st.session_state["agent_form_values"] = form_values
    current_user_id = _authenticated_user_id()
    if form_values.get("owner_user_id") is None and current_user_id is not None:
        form_values["owner_user_id"] = current_user_id
    with st.form("apmatia_agent_form"):
        st.subheader("Agent")
        left, right = st.columns(2)
        with left:
            name = st.text_input("Name", value=str(form_values["name"]))
            owner_user_id = st.number_input(
                "Owner user ID (0 = unassigned)",
                min_value=0,
                step=1,
                value=int(form_values["owner_user_id"] or 0),
            )
            owner_group_id = st.number_input(
                "Owner group ID (0 = unassigned)",
                min_value=0,
                step=1,
                value=int(form_values["owner_group_id"] or 0),
            )
            memory_id = st.number_input(
                "Memory ID",
                min_value=0,
                step=1,
                value=int(form_values["memory_id"]),
            )
            personality = st.text_area("Personality", value=str(form_values["personality"]), height=70)
            skills = st.text_area("Skills", value=str(form_values["skills"]), height=90)
            purpose = st.text_area("Purpose / Mission", value=str(form_values["purpose"]), height=90)
            backstory = st.text_area("Backstory", value=str(form_values["backstory"]), height=90)
            default_model_id = st.selectbox(
                "Default model",
                options=model_options,
                index=_model_option_index(model_options[1:], form_values["default_model_id"]),
                format_func=_model_option_label,
            )
        with right:
            active_model_id = st.selectbox(
                "Active model",
                options=model_options,
                index=_model_option_index(model_options[1:], form_values["active_model_id"]),
                format_func=_model_option_label,
            )
            workspace_root = st.text_input(
                "Workspace root",
                value=str(form_values["workspace_root"]),
                help="Absolute path where this agent should work.",
            )
            knowledge_root = st.text_input(
                "Knowledge root",
                value=str(form_values["knowledge_root"]),
                help="Absolute path where this agent should read and write knowledge.",
            )
            rag_root_ids = st.text_area(
                "RAG root IDs (JSON list)",
                value=_json_text(form_values["rag_root_ids"]),
                height=110,
            )
            tool_ids = st.text_area(
                "Tool IDs (JSON list)",
                value=_json_text(form_values["tool_ids"]),
                height=110,
            )
        with st.expander("Advanced prompt settings", expanded=False):
            communication_style = st.text_area("Communication style", value=str(form_values["communication_style"]), height=80)
            operating_principles = st.text_area("Operating principles", value=str(form_values["operating_principles"]), height=80)
            autonomy_level = st.text_area("Autonomy level", value=str(form_values["autonomy_level"]), height=70)
            decision_making_style = st.text_area("Decision making style", value=str(form_values["decision_making_style"]), height=80)
            memory_policy = st.text_area("Memory policy", value=str(form_values["memory_policy"]), height=80)
            domain_priorities = st.text_area("Domain priorities", value=str(form_values["domain_priorities"]), height=70)
            relationship_to_user = st.text_area("Relationship to user", value=str(form_values["relationship_to_user"]), height=80)
            tool_use_policy = st.text_area("Tool use policy", value=str(form_values["tool_use_policy"]), height=80)
            capability_boundaries = st.text_area("Capability boundaries", value=str(form_values["capability_boundaries"]), height=80)
            output_preferences = st.text_area("Output preferences", value=str(form_values["output_preferences"]), height=80)
            safety_ethics = st.text_area("Safety / ethics", value=str(form_values["safety_ethics"]), height=80)
            selfhood_truthfulness = st.text_area("Selfhood / truthfulness", value=str(form_values["selfhood_truthfulness"]), height=80)
            conflict_resolution_rules = st.text_area("Conflict resolution rules", value=str(form_values["conflict_resolution_rules"]), height=80)
            use_raw_prompt_override = st.checkbox("Use raw system prompt override", value=bool(form_values["use_raw_prompt_override"]))
            raw_prompt_override = st.text_area("Raw system prompt override", value=str(form_values["raw_prompt_override"]), height=160)

        metadata = st.text_area(
            "Metadata (JSON object)",
            value=_json_text(form_values["metadata"]),
            height=160,
        )

        submitted = st.form_submit_button("Save agent")

    if submitted:
        try:
            payload = {
                "name": name,
                "owner_user_id": None if int(owner_user_id) == 0 else int(owner_user_id),
                "owner_group_id": None if int(owner_group_id) == 0 else int(owner_group_id),
                "memory_id": int(memory_id),
                "rag_root_ids": _parse_json_field(rag_root_ids, []),
                "tool_ids": _parse_json_field(tool_ids, []),
                "default_model_id": (
                    None if default_model_id.get("id") is None else int(default_model_id.get("id"))
                ),
                "active_model_id": (
                    None if active_model_id.get("id") is None else int(active_model_id.get("id"))
                ),
                "workspace_root": workspace_root,
                "knowledge_root": knowledge_root,
                "metadata": _parse_json_field(metadata, {}),
                "prompt_id": form_values.get("prompt_id"),
                "personality": personality,
                "skills": skills,
                "purpose": purpose,
                "backstory": backstory,
                "communication_style": communication_style,
                "operating_principles": operating_principles,
                "autonomy_level": autonomy_level,
                "decision_making_style": decision_making_style,
                "memory_policy": memory_policy,
                "domain_priorities": domain_priorities,
                "relationship_to_user": relationship_to_user,
                "tool_use_policy": tool_use_policy,
                "capability_boundaries": capability_boundaries,
                "output_preferences": output_preferences,
                "safety_ethics": safety_ethics,
                "selfhood_truthfulness": selfhood_truthfulness,
                "conflict_resolution_rules": conflict_resolution_rules,
                "use_raw_prompt_override": use_raw_prompt_override,
                "raw_prompt_override": raw_prompt_override,
            }
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            st.error(f"Unable to parse agent form values: {error}")
        else:
            current_id = form_values.get("id")
            try:
                prompt_payload = {
                    "personality": personality,
                    "skills": skills,
                    "purpose": purpose,
                    "backstory": backstory,
                    "communication_style": communication_style,
                    "operating_principles": operating_principles,
                    "autonomy_level": autonomy_level,
                    "decision_making_style": decision_making_style,
                    "memory_policy": memory_policy,
                    "domain_priorities": domain_priorities,
                    "relationship_to_user": relationship_to_user,
                    "tool_use_policy": tool_use_policy,
                    "capability_boundaries": capability_boundaries,
                    "output_preferences": output_preferences,
                    "safety_ethics": safety_ethics,
                    "selfhood_truthfulness": selfhood_truthfulness,
                    "conflict_resolution_rules": conflict_resolution_rules,
                    "use_raw_prompt_override": use_raw_prompt_override,
                    "raw_prompt_override": raw_prompt_override,
                }
                if current_id is None:
                    prompt = create_agent_prompt(**prompt_payload)
                    payload["prompt_id"] = prompt["id"]
                    execute_module_command(f"{COMMAND_PREFIX}.create", **payload)
                else:
                    prompt_id = int(form_values.get("prompt_id") or 0)
                    if prompt_id:
                        update_agent_prompt(prompt_id, **prompt_payload)
                        payload["prompt_id"] = prompt_id
                    else:
                        prompt = create_agent_prompt(**prompt_payload)
                        payload["prompt_id"] = prompt["id"]
                    execute_module_command(
                        f"{COMMAND_PREFIX}.edit",
                        item_id=int(current_id),
                        **payload,
                    )
            except ApiError as error:
                st.error(f"Unable to save agent: {error.detail}")
            else:
                st.success("Agent saved.")
                st.session_state["agent_form_values"] = _empty_form_values()
                st.session_state["agent_selected_id"] = None
                st.rerun()

    prompt_preview = _build_prompt_preview(
        name=str(form_values["name"]) or "Agent",
        personality=str(form_values["personality"]),
        skills=str(form_values["skills"]),
        purpose=str(form_values["purpose"]),
        backstory=str(form_values["backstory"]),
        communication_style=str(form_values["communication_style"]),
        operating_principles=str(form_values["operating_principles"]),
        autonomy_level=str(form_values["autonomy_level"]),
        decision_making_style=str(form_values["decision_making_style"]),
        memory_policy=str(form_values["memory_policy"]),
        domain_priorities=str(form_values["domain_priorities"]),
        relationship_to_user=str(form_values["relationship_to_user"]),
        tool_use_policy=str(form_values["tool_use_policy"]),
        capability_boundaries=str(form_values["capability_boundaries"]),
        output_preferences=str(form_values["output_preferences"]),
        safety_ethics=str(form_values["safety_ethics"]),
        selfhood_truthfulness=str(form_values["selfhood_truthfulness"]),
        conflict_resolution_rules=str(form_values["conflict_resolution_rules"]),
        use_raw_prompt_override=bool(form_values["use_raw_prompt_override"]),
        raw_prompt_override=str(form_values["raw_prompt_override"]),
    )
    with st.expander("Compiled prompt preview", expanded=False):
        st.code(prompt_preview, language="text")

    st.divider()
    st.subheader("Directory checks")
    _render_directory_check("Workspace", str(form_values["workspace_root"]))
    _render_directory_check("Knowledge", str(form_values["knowledge_root"]))


def _render_directory_check(label: str, path_text: str) -> None:
    if not path_text.strip():
        st.info(f"{label} root is not set yet.")
        return
    path = Path(path_text).expanduser()
    if path.exists():
        st.success(f"{label} root exists: {path}")
    else:
        st.warning(f"{label} root does not exist yet: {path}")
