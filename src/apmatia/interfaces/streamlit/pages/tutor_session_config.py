"""Tutor session configuration page."""
from __future__ import annotations

import streamlit as st

from apmatia.interfaces.streamlit.api_client import ApiError, create_discussion, create_wiki, discussion_tree, list_agents, list_llm_configs, list_wikis, open_discussion, update_discussion
from apmatia.interfaces.streamlit.pages import discussion as discussion_page
from apmatia.interfaces.streamlit.pages.tutor_shared import discussion_controls, find_discussion, is_saved_tutor_discussion, wiki_label


def render() -> None:
    try:
        agents = list_agents()
        tree = discussion_tree()
        model_configs = list_llm_configs()
        wikis = list_wikis()
    except ApiError as error:
        st.error(f"Unable to load tutor workspace: {error.detail}")
        return

    st.title("Tutor Session Config")
    st.caption("Choose the tutor agent, discussion, and focused wiki for the active learning session.")

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
            discussion_controls(selected_agent, model_lookup)

        filtered_discussions = [
            discussion
            for discussion in discussions
            if is_saved_tutor_discussion(discussion)
            and discussion_page._discussion_belongs_to_agent(discussion, int(selected_agent.get("id")))
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

        selected_discussion_record = find_discussion(filtered_discussions, selected_discussion_id)
        focused_from_discussion = None if selected_discussion_record is None else selected_discussion_record.get("focused_wiki_id")
        if focused_from_discussion and not st.session_state.get("tutor_selected_wiki_id"):
            st.session_state["tutor_selected_wiki_id"] = focused_from_discussion

        with wiki_col:
            wiki_options = wikis or [{"id": None, "title": "Create a wiki to begin"}]
            selected_wiki = st.selectbox(
                "Focused wiki",
                options=wiki_options,
                index=discussion_page._selected_index(wiki_options, st.session_state.get("tutor_selected_wiki_id"), "id"),
                format_func=wiki_label,
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
