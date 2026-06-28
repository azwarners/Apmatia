"""Tutor page that pairs a discussion with a focused wiki."""
from __future__ import annotations

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    create_discussion,
    create_wiki,
    create_wiki_branch,
    create_wiki_leaf,
    delete_wiki_node,
    discussion_state,
    discussion_tree,
    get_wiki_tree,
    list_agents,
    list_llm_configs,
    list_wikis,
    open_discussion,
    prompt_discussion,
    search_wiki,
    stop_discussion,
    update_discussion,
    update_wiki_node,
)
from src.interfaces.streamlit.pages import discussion as discussion_page
from src.interfaces.streamlit.pages.tutor_shared import build_tutor_wiki_context, ensure_selected_node, render_tree, render_wiki_search, render_wiki_summary


def _find_discussion(discussions: list[dict[str, object]], discussion_id: object) -> dict[str, object] | None:
    for discussion in discussions:
        if str(discussion.get("discussion_id")) == str(discussion_id):
            return discussion
    return None


def render() -> None:
    discussion_page.apply_message_card_css()
    try:
        agents = list_agents()
        tree = discussion_tree()
        model_configs = list_llm_configs()
        wikis = list_wikis()
    except ApiError as error:
        st.error(f"Unable to load tutor workspace: {error.detail}")
        return

    st.title("Tutor")
    st.caption("Pair a tutoring discussion with one focused wiki so the agent and user can build structured notes together.")

    if not agents:
        st.info("Create an agent first so the tutor workspace can select a discussion partner.")
        return

    if "tutor_selected_agent_id" not in st.session_state:
        st.session_state["tutor_selected_agent_id"] = agents[0].get("id")
    if "tutor_clear_new_wiki_fields" not in st.session_state:
        st.session_state["tutor_clear_new_wiki_fields"] = False
    if st.session_state.get("tutor_clear_new_wiki_fields"):
        st.session_state["tutor_new_wiki_title"] = ""
        st.session_state["tutor_new_wiki_description"] = ""
        st.session_state["tutor_clear_new_wiki_fields"] = False

    model_lookup = {int(config.get("id")): config for config in model_configs if config.get("id") is not None}
    discussions = tree.get("discussions", [])

    with st.container(border=True):
        st.subheader("Tutor session")
        agent_col, discussion_col, wiki_col = st.columns(3)
        with agent_col:
            selected_agent = st.selectbox(
                "Agent",
                options=agents,
                index=discussion_page._selected_index(agents, st.session_state["tutor_selected_agent_id"], "id"),
                format_func=discussion_page._agent_label,
            )
            st.session_state["tutor_selected_agent_id"] = selected_agent.get("id")
            model_summary = discussion_page._selected_model_summary(selected_agent, model_lookup)
            if model_summary:
                st.caption(model_summary)

        filtered_discussions = [
            discussion
            for discussion in discussions
            if discussion_page._discussion_belongs_to_agent(discussion, int(selected_agent.get("id")))
            and bool(str(discussion.get("focused_wiki_id") or "").strip())
        ]
        backend_current_discussion_id = tree.get("current_discussion_id")
        current_discussion_id = backend_current_discussion_id
        if not any(str(item.get("discussion_id")) == str(current_discussion_id) for item in filtered_discussions):
            current_discussion_id = filtered_discussions[0].get("discussion_id") if filtered_discussions else None

        discussion_options = filtered_discussions if filtered_discussions else [{"discussion_id": None, "title": "No saved tutoring sessions for this agent yet"}]
        with discussion_col:
            selected_discussion = st.selectbox(
                "Discussion",
                options=discussion_options,
                index=discussion_page._selected_index(discussion_options, current_discussion_id, "discussion_id"),
                format_func=discussion_page._discussion_label,
            )
            selected_discussion_id = selected_discussion.get("discussion_id")

        if selected_discussion_id is not None and str(selected_discussion_id) != str(backend_current_discussion_id):
            try:
                open_discussion(str(selected_discussion_id))
            except ApiError as error:
                st.error(f"Unable to open discussion: {error.detail}")
            else:
                st.rerun()

        selected_discussion_record = _find_discussion(filtered_discussions, selected_discussion_id)
        focused_from_discussion = None if selected_discussion_record is None else selected_discussion_record.get("focused_wiki_id")
        if focused_from_discussion and not st.session_state.get("tutor_selected_wiki_id"):
            st.session_state["tutor_selected_wiki_id"] = focused_from_discussion

        with wiki_col:
            wiki_options = wikis or [{"id": None, "title": "Create a wiki to begin"}]
            selected_wiki = st.selectbox(
                "Focused wiki",
                options=wiki_options,
                index=discussion_page._selected_index(wiki_options, st.session_state.get("tutor_selected_wiki_id"), "id"),
                format_func=discussion_page._discussion_label if False else lambda wiki: f"{wiki.get('title') or 'Untitled Wiki'} (ID {wiki.get('id')})",
            )
            st.session_state["tutor_selected_wiki_id"] = selected_wiki.get("id")

        action_col_a, action_col_b = st.columns(2)
        with action_col_a:
            if st.button("Start new tutor discussion", use_container_width=True):
                if selected_wiki.get("id") is None:
                    st.warning("Select or create a wiki first.")
                else:
                    try:
                        created = create_discussion(
                            title=f"Tutoring: {selected_wiki.get('title') or 'Wiki'}",
                            group_id=None,
                            folder_id=None,
                            focused_wiki_id=str(selected_wiki["id"]),
                            agent_id=int(selected_agent.get("id")),
                        )
                    except ApiError as error:
                        st.error(f"Unable to create tutor discussion: {error.detail}")
                    else:
                        discussion_id = created.get("discussion", {}).get("discussion_id")
                        if discussion_id is not None:
                            open_discussion(str(discussion_id))
                        st.success(f"Created tutor discussion {discussion_id}.")
                        st.rerun()
        with action_col_b:
            if st.button(
                "Attach wiki to selected discussion",
                use_container_width=True,
                disabled=selected_discussion_id is None or selected_wiki.get("id") is None,
            ):
                try:
                    update_discussion(str(selected_discussion_id), focused_wiki_id=str(selected_wiki["id"]))
                except ApiError as error:
                    st.error(f"Unable to attach wiki: {error.detail}")
                else:
                    st.success("Tutor wiki attached to the discussion.")
                    st.rerun()

        with st.expander("Create a new wiki", expanded=False):
            new_wiki_title = st.text_input("Wiki title", key="tutor_new_wiki_title")
            new_wiki_description = st.text_area("Wiki description", key="tutor_new_wiki_description", height=100)
            if st.button("Create wiki", use_container_width=False):
                if not new_wiki_title.strip():
                    st.warning("Wiki title cannot be empty.")
                else:
                    try:
                        created = create_wiki(
                            title=new_wiki_title.strip(),
                            description=new_wiki_description.strip() or None,
                            owner_agent_id=int(selected_agent.get("id")),
                        )
                    except ApiError as error:
                        st.error(f"Unable to create wiki: {error.detail}")
                    else:
                        st.session_state["tutor_selected_wiki_id"] = created["wiki"]["id"]
                        st.session_state["tutor_clear_new_wiki_fields"] = True
                        st.success(f"Created wiki {created['wiki']['title']}.")
                        st.rerun()

    if selected_discussion_id is None:
        st.info("Start or select a discussion to begin tutoring.")
        return

    snapshot = {
        "discussion_id": None,
        "messages": [],
        "last_error": None,
        "is_streaming": False,
    }
    try:
        snapshot = discussion_state()
    except ApiError as error:
        st.error(f"Unable to load tutor discussion state: {error.detail}")
        return

    selected_wiki_id = st.session_state.get("tutor_selected_wiki_id") or focused_from_discussion
    wiki_tree = None
    selected_wiki_data = None
    if selected_wiki_id is not None:
        try:
            wiki_tree = get_wiki_tree(str(selected_wiki_id))
            selected_wiki_data = wiki_tree["wiki"]
        except ApiError as error:
            st.error(f"Unable to load focused wiki: {error.detail}")

    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Discussion")
        if focused_from_discussion:
            st.caption(f"Focused wiki ID for this discussion: {focused_from_discussion}")
        username = discussion_page._authenticated_username()
        agent_name = str(selected_agent.get("name") or "Tutor")
        initial_is_streaming = bool(snapshot.get("is_streaming"))
        if initial_is_streaming:
            snapshot = discussion_page._render_streaming_messages(username=username, agent_name=agent_name)
            st.caption(f"{agent_name} is typing...")
        else:
            discussion_page._render_messages(snapshot, username=username, agent_name=agent_name)
        if snapshot.get("last_error"):
            st.error(f"Last error: {snapshot['last_error']}")
        if bool(snapshot.get("is_streaming")):
            if st.button("Stop", use_container_width=False):
                try:
                    stop_discussion()
                except ApiError as error:
                    st.error(f"Unable to stop message: {error.detail}")
                else:
                    st.success("Message stopped.")
                    st.rerun()
            else:
                with st.form("apmatia_tutor_prompt_form"):
                    prompt = st.text_area("Message", height=140, placeholder="Ask the tutor a question or decide what to capture in the wiki.")
                    submitted = st.form_submit_button("Send message")
                if submitted:
                    if not prompt.strip():
                        st.warning("Please enter a message.")
                    else:
                        try:
                            wiki_context = build_tutor_wiki_context(selected_wiki_data, selected_node) if selected_wiki_data is not None else ""
                            prompt_discussion(
                                prompt=(
                                    f"{wiki_context}\n"
                                    f"User message: {prompt.strip()}"
                                ).strip(),
                                agent_id=int(selected_agent.get("id")),
                            )
                        except ApiError as error:
                            st.error(f"Unable to send message: {error.detail}")
                        else:
                            st.success("Message sent.")
                            st.rerun()

    with right:
        if wiki_tree is None or selected_wiki_data is None:
            st.info("Select or create a wiki, then attach it to the tutoring discussion.")
            return
        selected_node = ensure_selected_node(wiki_tree)
        st.subheader("Focused wiki")
        st.caption(f"Building notes in: {selected_wiki_data['title']}")
        st.caption(f"Root node ID: {selected_wiki_data.get('root_node_id')}")
        if selected_wiki_data.get("description"):
            st.write(str(selected_wiki_data["description"]))
        st.text_input("Search this wiki", key="tutor_wiki_search_query")
        query = st.session_state.get("tutor_wiki_search_query", "")
        if str(query).strip():
            try:
                results = search_wiki(str(selected_wiki_data["id"]), str(query).strip())
            except ApiError as error:
                st.error(f"Unable to search wiki: {error.detail}")
            else:
                if results:
                    st.caption(f"Found {len(results)} matching note(s).")
                else:
                    st.info("No wiki matches yet.")
        render_tree(wiki_tree["root"], selected_node_id=str(selected_node["id"]))
        st.divider()
        st.caption(f"Selected node: {selected_node['title']}")
        edited_title = st.text_input("Title", value=str(selected_node.get("title", "")), key=f"tutor-edit-title-{selected_node['id']}")
        edited_body = ""
        if selected_node["node_type"] == "leaf":
            edited_body = st.text_area(
                "Note body",
                value=str(selected_node.get("body", "")),
                height=260,
                key=f"tutor-edit-body-{selected_node['id']}",
            )
        save_col, delete_col = st.columns(2)
        with save_col:
            if st.button("Save selected node", use_container_width=True):
                try:
                    update_wiki_node(
                        str(selected_node["id"]),
                        title=edited_title,
                        body=edited_body if selected_node["node_type"] == "leaf" else "",
                    )
                except ApiError as error:
                    st.error(f"Unable to save wiki node: {error.detail}")
                else:
                    st.success("Wiki node saved.")
                    st.rerun()
        with delete_col:
            if st.button(
                "Delete selected node",
                use_container_width=True,
                disabled=str(selected_node["id"]) == str(wiki_tree["wiki"]["root_node_id"]),
            ):
                try:
                    delete_wiki_node(str(selected_node["id"]))
                except ApiError as error:
                    st.error(f"Unable to delete wiki node: {error.detail}")
                else:
                    st.session_state["tutor_selected_node_id"] = wiki_tree["root"]["id"]
                    st.success("Wiki node deleted.")
                    st.rerun()

        create_parent_id = selected_node["id"] if selected_node["node_type"] == "branch" else selected_node["parent_id"]
        if create_parent_id is not None:
            st.divider()
            create_col_a, create_col_b = st.columns(2)
            with create_col_a:
                new_branch_title = st.text_input("New section title", key="tutor_new_branch_title")
                if st.button("Add section", use_container_width=True):
                    if not new_branch_title.strip():
                        st.warning("Enter a section title first.")
                    else:
                        try:
                            create_wiki_branch(
                                str(selected_wiki_data["id"]),
                                parent_id=str(create_parent_id),
                                title=new_branch_title.strip(),
                            )
                        except ApiError as error:
                            st.error(f"Unable to add section: {error.detail}")
                        else:
                            st.session_state["tutor_new_branch_title"] = ""
                            st.success("Section added.")
                            st.rerun()
            with create_col_b:
                new_leaf_title = st.text_input("New note title", key="tutor_new_leaf_title")
                if st.button("Add note", use_container_width=True):
                    if not new_leaf_title.strip():
                        st.warning("Enter a note title first.")
                    else:
                        try:
                            created = create_wiki_leaf(
                                str(selected_wiki_data["id"]),
                                parent_id=str(create_parent_id),
                                title=new_leaf_title.strip(),
                                body="",
                            )
                        except ApiError as error:
                            st.error(f"Unable to add note: {error.detail}")
                        else:
                            st.session_state["tutor_new_leaf_title"] = ""
                            st.session_state["tutor_selected_node_id"] = created["node"]["id"]
                            st.success("Note added.")
                            st.rerun()
