"""Memory management page for viewing and editing persisted memories."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    archive_memory,
    create_memory,
    delete_memory,
    get_memory,
    list_agents,
    list_memories,
    search_memories,
    update_memory,
)


_VISIBILITY_OPTIONS = ["draft", "user_visible", "private"]
_STATUS_OPTIONS = ["active", "archived", "deleted"]


def _memory_label(memory: dict[str, Any]) -> str:
    return f"{memory.get('title') or 'Untitled'} (ID {memory.get('id')})"


def _memory_defaults(memory: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "id": None if memory is None else memory.get("id"),
        "title": "" if memory is None else memory.get("title", ""),
        "content": "" if memory is None else memory.get("content", ""),
        "tags": [] if memory is None else list(memory.get("tags", [])),
        "owner_agent_id": None if memory is None else memory.get("owner_agent_id"),
        "visibility": "draft" if memory is None else str(memory.get("visibility", "draft")),
        "status": "active" if memory is None else str(memory.get("status", "active")),
        "source_discussion_id": None if memory is None else memory.get("source_discussion_id"),
        "source_message_ids": [] if memory is None else list(memory.get("source_message_ids", [])),
    }


def _agent_label(agent: dict[str, Any]) -> str:
    return f"{agent.get('name') or 'Unnamed agent'} (ID {agent.get('id')})"


def _agent_name(agent_lookup: dict[int, dict[str, Any]], owner_agent_id: object) -> str:
    try:
        resolved_id = int(owner_agent_id) if owner_agent_id is not None else None
    except (TypeError, ValueError):
        resolved_id = None
    if resolved_id is None:
        return "Unassigned agent"
    agent = agent_lookup.get(resolved_id)
    if not agent:
        return f"Agent {resolved_id}"
    return str(agent.get("name") or f"Agent {resolved_id}")


def _selected_index(options: list[object], selected_value: object) -> int:
    if selected_value in options:
        return options.index(selected_value)
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


def _writable_agents(agents: list[dict[str, Any]], current_user_id: int | None) -> list[dict[str, Any]]:
    if current_user_id is None:
        return agents
    writable = []
    for agent in agents:
        try:
            owner_user_id = agent.get("owner_user_id")
            owner_group_id = agent.get("owner_group_id")
        except AttributeError:
            continue
        if owner_user_id == current_user_id:
            writable.append(agent)
            continue
        if owner_user_id is None and owner_group_id is None:
            # Legacy agents without ownership metadata stay visible.
            writable.append(agent)
    return writable


def render() -> None:
    st.title("Memory Management")
    st.caption("Browse memories by agent, user, or group, grouped by owning agent.")

    if "memory_query" not in st.session_state:
        st.session_state["memory_query"] = ""
    if "memory_agent_filter_id" not in st.session_state:
        st.session_state["memory_agent_filter_id"] = None
    if "memory_selected_id" not in st.session_state:
        st.session_state["memory_selected_id"] = None
    if "memory_editing_id" not in st.session_state:
        st.session_state["memory_editing_id"] = None

    try:
        agents = list_agents()
    except ApiError as error:
        st.error(f"Unable to load agents: {error.detail}")
        return

    current_user_id = _authenticated_user_id()
    writable_agents = _writable_agents(agents, current_user_id)

    agent_lookup = {
        int(agent.get("id")): agent
        for agent in agents
        if agent.get("id") is not None
    }

    agent_filter_options: list[object] = [None, *[agent.get("id") for agent in agents if agent.get("id") is not None]]
    agent_filter_labels = {
        None: "All agents",
        **{int(agent.get("id")): _agent_label(agent) for agent in agents if agent.get("id") is not None},
    }
    previous_agent_filter_id = st.session_state.get("memory_agent_filter_id")
    agent_filter = st.selectbox(
        "Agent filter",
        options=agent_filter_options,
        index=_selected_index(agent_filter_options, previous_agent_filter_id),
        format_func=lambda value: agent_filter_labels.get(value, f"Agent {value}"),
        key="memory_agent_filter_id",
    )
    if agent_filter != previous_agent_filter_id:
        st.session_state["memory_selected_id"] = None
        st.session_state["memory_editing_id"] = None

    search_col, refresh_col = st.columns([4, 1])
    with search_col:
        query = st.text_input("Search memories", value=str(st.session_state["memory_query"]))
    with refresh_col:
        refresh_clicked = st.button("Refresh", use_container_width=True)
    st.session_state["memory_query"] = query

    try:
        query_kwargs = {"include_archived": True}
        if agent_filter is not None:
            query_kwargs["owner_agent_id"] = agent_filter
        memories = search_memories(query, **query_kwargs) if query.strip() else list_memories(**query_kwargs)
    except ApiError as error:
        st.error(f"Unable to load memories: {error.detail}")
        return

    if refresh_clicked:
        st.rerun()

    left, right = st.columns([1.1, 1.4])
    with left:
        st.subheader("Memories")
        if st.button("Create new memory", use_container_width=True):
            st.session_state["memory_editing_id"] = None
            st.session_state["memory_selected_id"] = None
            st.rerun()
        if not memories:
            st.info("No memories found.")
        else:
            selected_memory = st.selectbox(
                "Select memory",
                options=memories,
                format_func=_memory_label,
                index=0 if st.session_state.get("memory_selected_id") is None else _selected_index(
                    [memory.get("id") for memory in memories],
                    st.session_state.get("memory_selected_id"),
                ),
            )
            selected_id = selected_memory.get("id")
            st.session_state["memory_selected_id"] = selected_id
            grouped_memories: dict[str, list[dict[str, Any]]] = {}
            for memory in memories:
                label = _agent_name(agent_lookup, memory.get("owner_agent_id"))
                grouped_memories.setdefault(label, []).append(memory)
            for agent_name in sorted(grouped_memories.keys()):
                st.write(f"**{agent_name}**")
                for memory in grouped_memories[agent_name]:
                    with st.container(border=True):
                        st.write(f"**{memory.get('title') or 'Untitled'}**")
                        st.caption(
                            f"ID {memory.get('id')} · owner agent {_agent_name(agent_lookup, memory.get('owner_agent_id'))} · "
                            f"{memory.get('visibility')} · {memory.get('status')}"
                        )
                        tags = ", ".join(memory.get("tags", []))
                        if tags:
                            st.caption(f"Tags: {tags}")
                        if st.button("Open", key=f"memory_open_{memory.get('id')}"):
                            st.session_state["memory_selected_id"] = memory.get("id")
                            st.session_state["memory_editing_id"] = memory.get("id")
                            st.rerun()

    with right:
        current_memory = None
        selected_id = st.session_state.get("memory_selected_id")
        if selected_id is not None:
            try:
                current_memory = get_memory(int(selected_id))
            except ApiError as error:
                st.error(f"Unable to load memory: {error.detail}")
                return

        editing_id = st.session_state.get("memory_editing_id")
        editing_memory = current_memory if editing_id == selected_id else None
        defaults = _memory_defaults(editing_memory)

        if current_memory is not None:
            st.subheader("Memory details")
            st.write(f"**{current_memory.get('title') or 'Untitled'}**")
            st.caption(
                f"Owner agent: {_agent_name(agent_lookup, current_memory.get('owner_agent_id'))} · "
                f"Visibility: {current_memory.get('visibility')} · Status: {current_memory.get('status')}"
            )
            st.write(current_memory.get("content") or "")
            tags = current_memory.get("tags") or []
            if tags:
                st.caption(f"Tags: {', '.join(tags)}")
            if st.button("Edit selected memory", use_container_width=True):
                st.session_state["memory_editing_id"] = current_memory.get("id")
                st.rerun()

        st.divider()
        st.subheader("Edit memory" if editing_memory is not None else "Create memory")
        with st.form("apmatia_memory_form"):
            title = st.text_input("Title", value=str(defaults["title"]))
            content = st.text_area("Content", value=str(defaults["content"]), height=180)
            tags_text = st.text_input("Tags (comma-separated)", value=", ".join(defaults["tags"]))
            owner_agent_options = [None, *[agent.get("id") for agent in writable_agents if agent.get("id") is not None]]
            owner_agent_labels = {
                None: "Unassigned agent",
                **{int(agent.get("id")): _agent_label(agent) for agent in writable_agents if agent.get("id") is not None},
            }
            if not writable_agents:
                st.info("No writable agents are available for this account.")
            selected_owner_agent_id = st.selectbox(
                "Owner agent",
                options=owner_agent_options,
                index=owner_agent_options.index(defaults["owner_agent_id"]) if defaults["owner_agent_id"] in owner_agent_options else 0,
                format_func=lambda value: owner_agent_labels.get(value, f"Agent {value}"),
            )
            visibility = st.selectbox(
                "Visibility",
                options=_VISIBILITY_OPTIONS,
                index=_VISIBILITY_OPTIONS.index(defaults["visibility"]),
            )
            status = st.selectbox(
                "Status",
                options=_STATUS_OPTIONS,
                index=_STATUS_OPTIONS.index(defaults["status"]),
            )
            source_discussion_id = st.text_input(
                "Source discussion ID",
                value="" if defaults["source_discussion_id"] is None else str(defaults["source_discussion_id"]),
            )
            source_message_ids = st.text_input(
                "Source message IDs (comma-separated)",
                value=", ".join(defaults["source_message_ids"]),
            )
            save_submitted = st.form_submit_button("Save memory" if editing_memory is not None else "Create memory")

        if save_submitted:
            payload = {
                "title": title,
                "content": content,
                "tags": [tag.strip() for tag in tags_text.split(",") if tag.strip()],
                "owner_agent_id": selected_owner_agent_id,
                "visibility": visibility,
                "status": status,
                "source_discussion_id": source_discussion_id.strip() or None,
                "source_message_ids": [item.strip() for item in source_message_ids.split(",") if item.strip()],
            }
            try:
                saved = (
                    update_memory(int(editing_memory.get("id")), **payload)
                    if editing_memory is not None
                    else create_memory(**payload)
                )
            except ApiError as error:
                st.error(f"Unable to save memory: {error.detail}")
            else:
                st.session_state["memory_selected_id"] = saved.get("id")
                st.session_state["memory_editing_id"] = saved.get("id")
                st.success(f"Saved memory {saved.get('id')} with status {saved.get('status')}.")
                st.rerun()

        if current_memory is not None:
            action_left, action_right = st.columns(2)
            with action_left:
                if st.button("Archive selected", use_container_width=True):
                    try:
                        archived = archive_memory(int(current_memory.get("id")))
                    except ApiError as error:
                        st.error(f"Unable to archive memory: {error.detail}")
                    else:
                        st.success(f"Archived memory {archived.get('id')}.")
                        st.rerun()
            with action_right:
                if st.button("Delete selected", use_container_width=True):
                    try:
                        deleted = delete_memory(int(current_memory.get("id")))
                    except ApiError as error:
                        st.error(f"Unable to delete memory: {error.detail}")
                    else:
                        st.success(f"Deleted memory {deleted.get('id')}.")
                        st.session_state["memory_selected_id"] = None
                        st.session_state["memory_editing_id"] = None
                        st.rerun()
