"""Tutor live discussion page."""
from __future__ import annotations

import streamlit as st

from apmatia.interfaces.streamlit.api_client import ApiError, discussion_state, get_wiki_tree, list_agents, prompt_discussion, stop_discussion
from apmatia.interfaces.streamlit.pages import discussion as discussion_page
from apmatia.interfaces.streamlit.pages.tutor_shared import build_tutor_wiki_context, ensure_selected_node, get_tutor_selected_agent_id


def render() -> None:
    try:
        agents = list_agents()
    except ApiError as error:
        st.error(f"Unable to load tutor discussion: {error.detail}")
        return

    st.title("Tutor Live Discussion")
    st.caption("Follow the active tutor conversation while keeping the session wiki nearby.")

    if not agents:
        st.info("Create an agent first so the tutor workspace can select a discussion partner.")
        return

    selected_agent_id = get_tutor_selected_agent_id(agents[0].get("id"))
    selected_agent = next((agent for agent in agents if str(agent.get("id")) == str(selected_agent_id)), agents[0])
    st.session_state["tutor_selected_agent_id"] = selected_agent.get("id")

    try:
        snapshot = discussion_state()
    except ApiError as error:
        st.error(f"Unable to load tutor discussion state: {error.detail}")
        return

    selected_wiki_id = st.session_state.get("tutor_selected_wiki_id")
    focused_wiki_id = snapshot.get("focused_wiki_id")
    if selected_wiki_id is None and focused_wiki_id is not None:
        selected_wiki_id = focused_wiki_id
        st.session_state["tutor_selected_wiki_id"] = focused_wiki_id

    st.subheader("Discussion")
    username = discussion_page._authenticated_username()
    agent_name = str(selected_agent.get("name") or "Tutor")
    if snapshot.get("discussion_id") is None:
        st.info("Open a tutor discussion from the session config page first.")
        return

    initial_is_streaming = bool(snapshot.get("is_streaming"))
    if initial_is_streaming:
        fragment_factory = getattr(st, "fragment", None)
        if getattr(fragment_factory, "__module__", "").startswith("streamlit"):
            activity_message_index = discussion_page._activity_message_index(
                snapshot.get("messages", []),
                snapshot.get("activity") if isinstance(snapshot.get("activity"), dict) else None,
            )
            discussion_page._render_message_history(
                snapshot,
                username=username,
                agent_name=agent_name,
                active_message_index=activity_message_index,
            )
            @fragment_factory(run_every=0.5)
            def _streaming_fragment() -> dict[str, object]:
                current_snapshot = discussion_page._render_streaming_messages(
                    username=username,
                    agent_name=agent_name,
                    include_history=False,
                )
                if current_snapshot.get("is_streaming"):
                    st.caption(f"{agent_name} is typing...")
                else:
                    st.rerun()
                return current_snapshot

            snapshot = _streaming_fragment()
        else:
            snapshot = discussion_page._render_streaming_messages(
                username=username,
                agent_name=agent_name,
                include_history=True,
            )
            st.caption(f"{agent_name} is typing...")
    else:
        discussion_page._render_messages(snapshot, username=username, agent_name=agent_name)

    if snapshot.get("last_error"):
        st.error(f"Last error: {snapshot['last_error']}")

    is_streaming = bool(snapshot.get("is_streaming"))
    if is_streaming:
        st.caption(f"{agent_name} is still responding. Use Stop to cancel the current stream.")
        if st.button("Stop", use_container_width=False):
            try:
                stop_discussion()
            except ApiError as error:
                st.error(f"Unable to stop message: {error.detail}")
                return
            st.success("Message stopped. Refreshing discussion.")
            st.rerun()
        return

    st.divider()
    with st.form("apmatia_tutor_prompt_form"):
        prompt = st.text_area("Message", height=140, placeholder="Ask the tutor a question or decide what to capture in the wiki.")
        submitted = st.form_submit_button("Send message")
    if submitted:
        if not prompt.strip():
            st.warning("Please enter a message.")
        else:
            try:
                wiki_context = ""
                if selected_wiki_id is not None:
                    try:
                        wiki_tree = get_wiki_tree(str(selected_wiki_id))
                        wiki_context = build_tutor_wiki_context(
                            wiki_tree["wiki"],
                            ensure_selected_node(wiki_tree),
                        )
                    except ApiError:
                        wiki_context = f"focused_wiki_id: {selected_wiki_id}"
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
