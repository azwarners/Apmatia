"""Tutor session wiki browser page."""
from __future__ import annotations

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_wiki_branch,
    create_wiki_leaf,
    delete_wiki_node,
    discussion_state,
    flatten_wiki_tree,
    get_wiki_tree,
    list_wikis,
    prompt_discussion,
    move_wiki_node,
    update_wiki_node,
)
from apmatia.interfaces.streamlit.pages import discussion as discussion_page
from apmatia.interfaces.streamlit.pages.tutor_shared import (
    apply_wiki_tree_css,
    build_tutor_wiki_context,
    ensure_selected_node,
    render_tree,
    render_wiki_search,
    render_wiki_summary,
    wiki_label,
)


def render() -> None:
    try:
        wikis = list_wikis()
    except ApiError as error:
        st.error(f"Unable to load wikis: {error.detail}")
        return

    st.title("Tutor Session Wiki")
    st.caption("Browse tutor knowledge as a collapsible tree with search and editable note nodes.")

    if not wikis:
        st.info("Create a wiki in Tutor Session Config first.")
        return

    if "tutor_selected_wiki_id" not in st.session_state:
        st.session_state["tutor_selected_wiki_id"] = wikis[0].get("id")
    if "tutor_wiki_mode" not in st.session_state:
        st.session_state["tutor_wiki_mode"] = "view"

    selected_wiki = st.selectbox(
        "Wiki",
        options=wikis,
        index=next((i for i, wiki in enumerate(wikis) if wiki.get("id") == st.session_state.get("tutor_selected_wiki_id")), 0),
        format_func=wiki_label,
    )
    st.session_state["tutor_selected_wiki_id"] = selected_wiki.get("id")
    st.toggle("Edit mode", value=st.session_state["tutor_wiki_mode"] == "edit", key="tutor_wiki_mode_toggle")
    st.session_state["tutor_wiki_mode"] = "edit" if st.session_state.get("tutor_wiki_mode_toggle") else "view"

    try:
        wiki_tree = get_wiki_tree(str(selected_wiki["id"]))
    except ApiError as error:
        st.error(f"Unable to load wiki tree: {error.detail}")
        return

    render_wiki_summary(wiki_tree["wiki"])
    render_wiki_search(wiki_tree["wiki"])
    apply_wiki_tree_css()

    selected_node = ensure_selected_node(wiki_tree)
    try:
        move_targets = flatten_wiki_tree(str(selected_wiki["id"]))
    except ApiError:
        move_targets = []
    st.divider()
    st.subheader("Knowledge tree")
    st.caption("Build the shape first. Then fill each branch with the tutor.")
    render_tree(
        wiki_tree["root"],
        selected_node_id=str(selected_node["id"]),
    )

    if st.session_state["tutor_wiki_mode"] == "edit":
        st.divider()
        st.caption(f"Selected node: {selected_node['title']}")
        with st.expander("Node actions", expanded=False, key="tutor-wiki-node-actions"):
            edited_title = st.text_input("Title", value=str(selected_node.get("title", "")), key=f"tutor-edit-title-{selected_node['id']}")
            edited_body = ""
            if selected_node["node_type"] == "leaf":
                edited_body = st.text_area("Note body", value=str(selected_node.get("body", "")), height=220, key=f"tutor-edit-body-{selected_node['id']}")
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

        with st.expander("Ask the agent", expanded=False, key="tutor-wiki-ask-agent"):
            help_prompt = st.text_area(
                "Ask the agent to help fill this branch",
                value="Please help me fill these ideas in with the knowledge I am looking for. Suggest missing subtopics, definitions, and a useful structure.",
                height=130,
                key="tutor_wiki_help_prompt",
            )
            if st.button("Ask agent to help", use_container_width=True):
                try:
                    discussion_state_snapshot = discussion_state()
                    agent_id = None
                    if isinstance(discussion_state_snapshot, dict):
                        agent_id = st.session_state.get("tutor_selected_agent_id")
                    prompt_discussion(
                        prompt=(
                            "Help me fill out the selected wiki branch with organized knowledge.\n"
                            f"{build_tutor_wiki_context(wiki_tree['wiki'], selected_node)}\n"
                            f"Context: {help_prompt.strip()}\n"
                            "Please propose a concise outline and any missing child topics or example explanations.\n"
                            "If you want to add a new top-level branch, use parent_id equal to the root_node_id."
                        ),
                        agent_id=int(agent_id) if agent_id is not None else None,
                    )
                except ApiError as error:
                    st.error(f"Unable to ask the tutor for help: {error.detail}")
                else:
                    st.success("Tutor prompt sent. Check the live discussion page for the response.")
    else:
        st.info("View mode: expand a branch to browse. Switch to Edit mode when you want to add, move, or rename nodes.")
