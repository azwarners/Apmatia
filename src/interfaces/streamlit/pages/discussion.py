"""Discussion page for sending prompts through the discussion backend."""
from __future__ import annotations

import base64
import json
from typing import Any

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    delete_discussion_message,
    create_discussion,
    delete_discussion,
    discussion_state,
    discussion_tree,
    list_agents,
    list_llm_configs,
    open_discussion,
    prompt_discussion,
    pause_group_chat,
    resume_group_chat,
    set_discussion_group_chat_mode,
    update_discussion,
    stop_discussion,
    update_discussion_message,
)
from src.interfaces.streamlit.components.message_card import (
    MessageCardActions,
    apply_message_card_css,
    render_message_text_block,
    render_message_card,
)
from src.interfaces.streamlit.components.clipboard_button import (
    render_clipboard_image_paste_bridge,
)


def _agent_label(agent: dict[str, object]) -> str:
    agent_id = agent.get("id")
    name = agent.get("name") or "Unnamed agent"
    return f"{name} (ID {agent_id})"


def _discussion_label(discussion: dict[str, object]) -> str:
    discussion_id = discussion.get("discussion_id")
    title = discussion.get("title") or "Untitled Discussion"
    return f"{title} (ID {discussion_id})"


def _discussion_belongs_to_agent(discussion: dict[str, object], agent_id: int | None) -> bool:
    if agent_id is None:
        return True
    participant_agent_ids = discussion.get("participant_agent_ids") or []
    if not participant_agent_ids:
        return False
    return int(agent_id) in {
        int(candidate)
        for candidate in participant_agent_ids
        if candidate is not None
    }


def _selected_model_summary(
    agent: dict[str, object],
    model_lookup: dict[int, dict[str, object]],
) -> str | None:
    model_id = agent.get("active_model_id")
    if model_id is None:
        model_id = agent.get("default_model_id")
    try:
        resolved_model_id = int(model_id) if model_id is not None else None
    except (TypeError, ValueError):
        resolved_model_id = None
    if resolved_model_id is None:
        return None

    config = model_lookup.get(resolved_model_id)
    if not config:
        return f"Selected model ID {resolved_model_id} is not available."

    alias = str(config.get("user_alias") or "Unnamed model")
    backend = str(config.get("backend") or "unknown")
    model_url = str(config.get("model_url") or "").strip() or "not configured"
    return f"Using {alias} via {backend} at {model_url}."


def _selected_index(options: list[dict[str, object]], selected_id: object, key: str) -> int:
    for index, option in enumerate(options):
        if option.get(key) == selected_id:
            return index
    return 0 if options else 0


def _participant_label(agent_id: object, agent_lookup: dict[int, dict[str, object]]) -> str:
    try:
        resolved_agent_id = int(agent_id)
    except (TypeError, ValueError):
        return f"Agent {agent_id}"
    agent = agent_lookup.get(resolved_agent_id)
    if not agent:
        return f"Agent {resolved_agent_id}"
    return _agent_label(agent)


def _speaker_agent(
    speaker_name: str | None,
    agent_lookup: dict[int, dict[str, object]],
) -> dict[str, object] | None:
    if not speaker_name:
        return None
    target = speaker_name.strip().lower()
    for agent in agent_lookup.values():
        name = str(agent.get("name") or "").strip().lower()
        if name == target:
            return agent
    return None


def _render_message_attachments(message: dict[str, object]) -> None:
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        return

    raw_attachments = metadata.get("attachments")
    if not isinstance(raw_attachments, list) or not raw_attachments:
        return

    for attachment in raw_attachments:
        if not isinstance(attachment, dict):
            continue
        data_url = str(attachment.get("data_url") or "").strip()
        if not data_url:
            continue
        filename = str(attachment.get("filename") or "image").strip() or "image"
        st.image(data_url, caption=filename, use_container_width=True)


def _uploaded_images_to_payload(uploaded_files: list[Any] | None) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    if not uploaded_files:
        return payload

    for uploaded_file in uploaded_files:
        name = str(getattr(uploaded_file, "name", "") or "image")
        mime_type = str(getattr(uploaded_file, "type", "") or "image/png")
        data = uploaded_file.getvalue()
        payload.append(
            {
                "filename": name,
                "mime_type": mime_type,
                "data_base64": base64.b64encode(data).decode("ascii"),
            }
        )
    return payload


MODE_DESCRIPTIONS = {
    "single": "One selected agent replies, and the discussion stops for your next message.",
    "round_robin": "Each participant speaks once in order, then the discussion waits for you.",
    "auto_paced": "Participants keep taking turns automatically. Use the pause toggle to control the delay.",
    "continuous": "Participants keep taking turns automatically with no pause between turns.",
    "direct": "Participants answer directly when addressed. The exchange can stop on its own.",
}


def _authenticated_username() -> str:
    session = st.session_state.get("authenticated_user")
    if isinstance(session, dict):
        username = session.get("username")
        if username:
            return str(username)
    return "User"


def _message_title(role: str, *, username: str, agent_name: str, speaker_name: str | None = None) -> str:
    role_key = role.strip().lower()
    if role_key == "user":
        return username
    if role_key in {"assistant", "agent"}:
        return speaker_name or agent_name
    return role


def _format_model_reference(agent: dict[str, object], model_lookup: dict[int, dict[str, object]]) -> str | None:
    model_summary = _selected_model_summary(agent, model_lookup)
    if model_summary is None:
        return None
    return model_summary.removeprefix("Using ").rstrip(".")


def _format_llama_server_phase(status: dict[str, object] | None) -> str | None:
    if not isinstance(status, dict):
        return None

    chat_format = str(status.get("chat_format") or "").strip()
    thinking_enabled = status.get("thinking_enabled")
    selected_slot_id = status.get("selected_slot_id")
    current_task_id = status.get("current_task_id")
    prompt_progress = status.get("prompt_processing_progress")
    prompt_tokens = status.get("prompt_processing_n_tokens") or status.get("prompt_processing_done_tokens")
    prompt_total = status.get("prompt_tokens_total")
    prompt_eval = status.get("prompt_eval") if isinstance(status.get("prompt_eval"), dict) else {}
    eval_stats = status.get("eval") if isinstance(status.get("eval"), dict) else {}
    total_tokens = status.get("total_tokens")
    total_time_ms = status.get("total_time_ms")

    pieces: list[str] = []
    if chat_format:
        pieces.append(f"chat format {chat_format}")
    if thinking_enabled is True:
        pieces.append("thinking on")
    elif thinking_enabled is False:
        pieces.append("thinking off")

    if selected_slot_id is not None and current_task_id is not None:
        pieces.append(f"slot {selected_slot_id} task {current_task_id}")

    phase_bits: list[str] = []
    if prompt_progress is not None:
        phase = "processing prompt" if float(prompt_progress) < 1.0 else "prompt processed"
        phase_bits.append(phase)
        phase_bits.append(f"{float(prompt_progress) * 100:.1f}%")
        if prompt_tokens is not None and prompt_total is not None:
            phase_bits.append(f"{int(prompt_tokens)}/{int(prompt_total)} tokens")
        elif prompt_tokens is not None:
            phase_bits.append(f"{int(prompt_tokens)} tokens")
    elif eval_stats.get("tokens_per_second") is not None:
        phase_bits.append("generating response")

    prompt_tps = prompt_eval.get("tokens_per_second")
    if prompt_tps is not None:
        phase_bits.append(f"prompt {float(prompt_tps):.2f} tok/s")
    eval_tps = eval_stats.get("tokens_per_second")
    if eval_tps is not None:
        phase_bits.append(f"generation {float(eval_tps):.2f} tok/s")
    if total_tokens is not None and total_time_ms is not None:
        phase_bits.append(f"total {int(total_tokens)} tokens / {float(total_time_ms) / 1000.0:.2f}s")

    if phase_bits:
        pieces.append(", ".join(phase_bits))
    if status.get("slots_idle") is True:
        pieces.append("idle")

    return " | ".join(pieces) if pieces else None


def _message_llama_server_status(
    message: dict[str, object],
    *,
    activity: dict[str, object] | None,
    llama_server_status: dict[str, object] | None,
) -> dict[str, object] | None:
    role = str(message.get("role", "Assistant")).strip().lower()
    if role == "user":
        return None

    if isinstance(activity, dict):
        activity_speaker = str(activity.get("speaker_name") or "").strip().lower()
        message_speaker = str(message.get("speaker_name") or "").strip().lower()
        if activity_speaker and message_speaker and activity_speaker == message_speaker and isinstance(llama_server_status, dict):
            return llama_server_status

    metadata = message.get("metadata")
    if isinstance(metadata, dict):
        payload = metadata.get("llama_server_status")
        if isinstance(payload, dict):
            return payload

    return None


def _activity_matches_message(
    message: dict[str, object],
    activity: dict[str, object] | None,
) -> bool:
    if not isinstance(activity, dict):
        return False

    role = str(message.get("role", "Assistant")).strip().lower()
    if role == "user":
        return False

    activity_speaker = str(activity.get("speaker_name") or "").strip().lower()
    message_speaker = str(message.get("speaker_name") or "").strip().lower()
    if not activity_speaker or not message_speaker:
        return False
    return activity_speaker == message_speaker


def _activity_status_text(
    activity: dict[str, object] | None,
    *,
    agent_lookup: dict[int, dict[str, object]],
    model_lookup: dict[int, dict[str, object]],
    llama_server_status: dict[str, object] | None = None,
) -> str | None:
    if not isinstance(activity, dict):
        return None

    speaker_name = activity.get("speaker_name")
    stage = str(activity.get("stage") or "").strip().lower()
    agent = _speaker_agent(str(speaker_name) if speaker_name is not None else None, agent_lookup)
    model_summary = None if agent is None else _format_model_reference(agent, model_lookup)
    agent_name = str(activity.get("agent_name") or speaker_name or "Agent").strip()

    tool = activity.get("tool")

    if stage == "tool" and isinstance(tool, dict):
        tool_name = str(tool.get("name") or "tool")
        tool_status = str(tool.get("status") or "running")
        arguments = tool.get("arguments")
        bits = [f"{agent_name} is executing {tool_name} ({tool_status})."]
        if model_summary:
            bits.append(f"Model: {model_summary}.")
        if arguments is not None:
            bits.append(f"Parameters: {json.dumps(arguments, ensure_ascii=False, sort_keys=True)}.")
        server_summary = _format_llama_server_phase(llama_server_status)
        if server_summary:
            bits.append(server_summary + ".")
        return " ".join(bits)

    if stage == "generating" or stage == "prompt":
        phase = "processing prompt" if stage == "prompt" else "generating a response"
        bits = [f"{agent_name} is {phase}."]
        server_summary = _format_llama_server_phase(llama_server_status)
        if server_summary:
            bits.append(server_summary + ".")
        if model_summary:
            bits.append(f"Model: {model_summary}.")
        return " ".join(bits) if bits else None

    if agent_name:
        return f"{agent_name} is active."
    return None


def _render_message_card(
    discussion_id: str,
    index: int,
    message: dict[str, object],
    *,
    username: str,
    agent_name: str,
    agent_lookup: dict[int, dict[str, object]] | None = None,
    model_lookup: dict[int, dict[str, object]] | None = None,
    activity: dict[str, object] | None = None,
    llama_server_status: dict[str, object] | None = None,
    is_active_message: bool = False,
) -> None:
    agent_lookup = agent_lookup or {}
    model_lookup = model_lookup or {}
    text = str(message.get("text", ""))
    role = str(message.get("role", "Assistant"))
    speaker_name = message.get("speaker_name") if isinstance(message.get("speaker_name"), str) else None
    title = _message_title(
        role,
        username=username,
        agent_name=agent_name,
        speaker_name=speaker_name,
    )
    subtitle = None
    if role.strip().lower() != "user":
        speaker_agent = _speaker_agent(speaker_name, agent_lookup)
        if speaker_agent is not None:
            subtitle = _format_model_reference(speaker_agent, model_lookup)
    if _activity_matches_message(message, activity):
        subtitle = _activity_status_text(activity, agent_lookup=agent_lookup, model_lookup=model_lookup) or subtitle
    message_status = _message_llama_server_status(
        message,
        activity=activity,
        llama_server_status=llama_server_status,
    )
    if is_active_message and isinstance(llama_server_status, dict) and _activity_matches_message(message, activity):
        message_status = llama_server_status
    details = None
    if _activity_matches_message(message, activity) and isinstance(activity, dict):
        tool = activity.get("tool")
        if isinstance(tool, dict) and tool:
            details = lambda tool=tool: st.json(tool)
    edit_target = st.session_state.get("discussion_edit_target")
    delete_target = st.session_state.get("discussion_delete_target")

    def _set_edit_target(message_text: str) -> None:
        st.session_state["discussion_edit_target"] = {
            "discussion_id": discussion_id,
            "index": index,
            "text": message_text,
        }
        st.rerun()

    def _set_delete_target(message_text: str) -> None:
        st.session_state["discussion_delete_target"] = {
            "discussion_id": discussion_id,
            "index": index,
            "text": message_text,
        }
        st.rerun()

    def _render_body() -> None:
        if isinstance(edit_target, dict) and edit_target.get("discussion_id") == discussion_id and edit_target.get("index") == index:
            new_text = st.text_area(
                "Edit message",
                value=str(edit_target.get("text", "")),
                height=160,
                key=f"discussion-edit-inline-{discussion_id}-{index}",
                label_visibility="collapsed",
            )
            button_left, button_right, _ = st.columns([1, 1, 10])
            with button_left:
                if st.button("Cancel", key=f"edit-cancel-{discussion_id}-{index}", width="content"):
                    st.session_state.pop("discussion_edit_target", None)
                    st.rerun()
            with button_right:
                if st.button("Save", key=f"edit-save-{discussion_id}-{index}", width="content"):
                    try:
                        update_discussion_message(discussion_id, index, new_text)
                    except ApiError as error:
                        st.error(f"Unable to update message: {error.detail}")
                    else:
                        st.session_state.pop("discussion_edit_target", None)
                        st.success("Message updated.")
                        st.rerun()
        else:
            render_message_text_block(text)
            _render_message_attachments(message)
        stats_caption = _format_llama_server_phase(message_status)
        if stats_caption:
            st.caption(stats_caption)

        if isinstance(delete_target, dict) and delete_target.get("discussion_id") == discussion_id and delete_target.get("index") == index:
            st.warning("Delete this message?")
            cancel_col, delete_col, _ = st.columns([1, 1, 8])
            with cancel_col:
                if st.button("Cancel", key=f"delete-cancel-{discussion_id}-{index}", width="content"):
                    st.session_state.pop("discussion_delete_target", None)
                    st.rerun()
            with delete_col:
                if st.button("Delete", key=f"delete-save-{discussion_id}-{index}", width="content", type="primary"):
                    try:
                        delete_discussion_message(discussion_id, index)
                    except ApiError as error:
                        st.error(f"Unable to delete message: {error.detail}")
                    else:
                        st.session_state.pop("discussion_delete_target", None)
                        st.success("Message deleted.")
                        st.rerun()

    render_message_card(
        title=title,
        message_text=text,
        card_key=f"discussion-{discussion_id}-{index}",
        subtitle=subtitle,
        actions=MessageCardActions(
            on_copy=lambda _message_text: None,
            on_edit=_set_edit_target,
            on_delete=_set_delete_target,
        ),
        content=_render_body,
        details=details,
        details_label="Prompt and tool details",
    )


def _render_live_activity_card(
    discussion_id: str,
    *,
    activity: dict[str, object],
    agent_lookup: dict[int, dict[str, object]] | None = None,
    model_lookup: dict[int, dict[str, object]] | None = None,
    llama_server_status: dict[str, object] | None = None,
) -> None:
    agent_lookup = agent_lookup or {}
    model_lookup = model_lookup or {}
    agent_name = str(activity.get("agent_name") or activity.get("speaker_name") or "Agent").strip()
    speaker_name = str(activity.get("speaker_name") or "").strip()
    speaker_agent = _speaker_agent(speaker_name or None, agent_lookup)
    subtitle = None if speaker_agent is None else _format_model_reference(speaker_agent, model_lookup)
    details = None
    tool = activity.get("tool")
    if isinstance(tool, dict) and tool:
        details = lambda tool=tool: st.json(tool)

    def _render_body() -> None:
        activity_text = _activity_status_text(
            activity,
            agent_lookup=agent_lookup,
            model_lookup=model_lookup,
            llama_server_status=llama_server_status,
        )
        if activity_text:
            st.caption(activity_text)
        elif isinstance(llama_server_status, dict):
            phase = _format_llama_server_phase(llama_server_status)
            if phase:
                st.caption(phase)

    render_message_card(
        title=agent_name,
        message_text="",
        card_key=f"discussion-{discussion_id}-live-activity",
        subtitle=subtitle,
        actions=None,
        content=_render_body,
        details=details,
        details_label="Prompt and tool details",
    )


def _render_messages(
    snapshot: dict[str, object],
    *,
    username: str,
    agent_name: str,
    agent_lookup: dict[int, dict[str, object]] | None = None,
    model_lookup: dict[int, dict[str, object]] | None = None,
) -> None:
    agent_lookup = agent_lookup or {}
    model_lookup = model_lookup or {}
    messages = snapshot.get("messages", [])
    if not messages:
        st.info("No messages yet.")
        return

    discussion_id = str(snapshot.get("discussion_id", ""))
    activity = snapshot.get("activity") if isinstance(snapshot.get("activity"), dict) else None
    llama_server_status = (
        snapshot.get("llama_server_status") if isinstance(snapshot.get("llama_server_status"), dict) else None
    )
    activity_message_index = None
    if isinstance(activity, dict):
        activity_speaker = str(activity.get("speaker_name") or "").strip().lower()
        if activity_speaker:
            for index in range(len(messages) - 1, -1, -1):
                candidate = messages[index]
                if _activity_matches_message(candidate, activity):
                    activity_message_index = index
                    break
    for index, message in enumerate(messages):
        is_active_message = activity_message_index is not None and index == activity_message_index
        _render_message_card(
            discussion_id,
            index,
            message,
            username=username,
            agent_name=agent_name,
            agent_lookup=agent_lookup,
            model_lookup=model_lookup,
            activity=activity if is_active_message else None,
            llama_server_status=llama_server_status if is_active_message else None,
            is_active_message=bool(snapshot.get("is_streaming")) and is_active_message,
        )
    if (
        bool(snapshot.get("is_streaming"))
        and isinstance(activity, dict)
        and activity_message_index is None
    ):
        _render_live_activity_card(
            discussion_id,
            activity=activity,
            agent_lookup=agent_lookup,
            model_lookup=model_lookup,
            llama_server_status=llama_server_status,
        )


def _render_streaming_messages(
    *,
    username: str,
    agent_name: str,
    agent_lookup: dict[int, dict[str, object]] | None = None,
    model_lookup: dict[int, dict[str, object]] | None = None,
) -> dict[str, object]:
    agent_lookup = agent_lookup or {}
    model_lookup = model_lookup or {}
    snapshot = discussion_state()
    _render_messages(
        snapshot,
        username=username,
        agent_name=agent_name,
        agent_lookup=agent_lookup,
        model_lookup=model_lookup,
    )
    return snapshot


def render() -> None:
    apply_message_card_css()
    try:
        agents = list_agents()
        tree = discussion_tree()
        model_configs = list_llm_configs()
    except ApiError as error:
        st.error(f"Unable to load discussion data: {error.detail}")
        return

    st.title("Discussion")
    st.caption("Choose an Agent, select a discussion, and send prompts through the discussion backend.")

    if not agents:
        st.info("Create an agent first so the discussion can resolve a model automatically.")
        return

    model_lookup = {
        int(config.get("id")): config
        for config in model_configs
        if config.get("id") is not None
    }

    discussions = tree.get("discussions", [])

    if "discussion_selected_agent_id" not in st.session_state:
        st.session_state["discussion_selected_agent_id"] = agents[0].get("id")

    with st.container(border=True):
        st.subheader("Discussion controls")
        left, right = st.columns(2)
        with left:
            selected_agent = st.selectbox(
                "Agent",
                options=agents,
                index=_selected_index(agents, st.session_state["discussion_selected_agent_id"], "id"),
                format_func=_agent_label,
            )
            selected_agent_id = selected_agent.get("id")
            st.session_state["discussion_selected_agent_id"] = selected_agent_id
            model_summary = _selected_model_summary(selected_agent, model_lookup)
            if model_summary:
                st.caption(model_summary)
        with right:
            filtered_discussions = [
                discussion
                for discussion in discussions
                if _discussion_belongs_to_agent(discussion, int(selected_agent_id))
            ]
            backend_current_discussion_id = tree.get("current_discussion_id")
            current_discussion_id = backend_current_discussion_id
            if not any(
                str(discussion.get("discussion_id")) == str(current_discussion_id)
                for discussion in filtered_discussions
            ):
                current_discussion_id = (
                    filtered_discussions[0].get("discussion_id")
                    if filtered_discussions
                    else None
                )
            discussion_options = discussions or [{"discussion_id": None, "title": "Create a new discussion"}]
            if filtered_discussions:
                discussion_options = filtered_discussions
            else:
                discussion_options = [{"discussion_id": None, "title": "No discussions for this agent yet"}]
            selected_discussion = st.selectbox(
                "Discussion",
                options=discussion_options,
                index=_selected_index(discussion_options, current_discussion_id, "discussion_id"),
                format_func=_discussion_label,
            )
            selected_discussion_id = selected_discussion.get("discussion_id")

        if selected_discussion_id is not None and str(selected_discussion_id) != str(backend_current_discussion_id):
            try:
                open_discussion(str(selected_discussion_id))
            except ApiError as error:
                st.error(f"Unable to open discussion: {error.detail}")
            else:
                st.rerun()

        start_col, delete_col = st.columns(2)
        with start_col:
            if st.button("Start a new discussion", use_container_width=True):
                try:
                    created = create_discussion(
                        title="New Discussion",
                        group_id=None,
                        folder_id=None,
                        agent_id=int(selected_agent_id),
                    )
                except ApiError as error:
                    st.error(f"Unable to create discussion: {error.detail}")
                    return
                discussion_id = created.get("discussion", {}).get("discussion_id")
                if discussion_id is not None:
                    try:
                        open_discussion(str(discussion_id))
                    except ApiError:
                        pass
                st.success(f"Created discussion {discussion_id}.")
                st.rerun()
        with delete_col:
            if st.button(
                "Delete selected discussion",
                use_container_width=True,
                disabled=selected_discussion_id is None,
            ):
                discussion_id = selected_discussion.get("discussion_id")
                if discussion_id is None:
                    st.warning("Select a discussion to delete.")
                    return
                try:
                    deleted = delete_discussion(str(discussion_id))
                except ApiError as error:
                    st.error(f"Unable to delete discussion: {error.detail}")
                    return
                next_discussion_id = deleted.get("result", {}).get("next_discussion_id")
                if next_discussion_id is None:
                    remaining_discussions = [
                        discussion
                        for discussion in filtered_discussions
                        if str(discussion.get("discussion_id")) != str(discussion_id)
                    ]
                    next_discussion_id = (
                        remaining_discussions[0].get("discussion_id")
                        if remaining_discussions
                        else None
                    )
                if next_discussion_id is not None:
                    try:
                        open_discussion(str(next_discussion_id))
                    except ApiError:
                        pass
                st.session_state.pop("discussion_edit_target", None)
                st.session_state.pop("discussion_delete_target", None)
                st.success("Discussion moved to trash.")
                st.rerun()

    snapshot: dict[str, object] = {
        "discussion_id": None,
        "messages": [],
        "last_error": None,
        "is_streaming": False,
        "chat_mode": "single",
        "chat_pause_seconds": None,
        "chat_is_paused": False,
        "chat_turn_index": 0,
        "chat_coordinator_agent_id": None,
    }
    if selected_discussion_id is not None:
        try:
            snapshot = discussion_state()
        except ApiError as error:
            st.error(f"Unable to load discussion state: {error.detail}")
            return

    if selected_discussion_id is not None:
        current_chat_mode = str(selected_discussion.get("chat_mode") or snapshot.get("chat_mode") or "single")
        current_pause_seconds = selected_discussion.get("chat_pause_seconds")
        current_coordinator_agent_id = selected_discussion.get("chat_coordinator_agent_id")
        current_participant_ids = [
            int(candidate)
            for candidate in (selected_discussion.get("participant_agent_ids") or [])
            if candidate is not None
        ]
        agent_lookup = {
            int(agent["id"]): agent
            for agent in agents
            if agent.get("id") is not None
        }
        with st.container(border=True):
            st.subheader("Participants")
            participant_options = list(agent_lookup.keys())
            default_participant_ids = [
                agent_id for agent_id in current_participant_ids if agent_id in agent_lookup
            ]
            if not default_participant_ids and int(selected_agent_id) in agent_lookup:
                default_participant_ids = [int(selected_agent_id)]
            selected_participant_ids = st.multiselect(
                "Discussion participants",
                options=participant_options,
                default=default_participant_ids,
                format_func=lambda agent_id: _participant_label(agent_id, agent_lookup),
                key=f"discussion-participants-{selected_discussion_id}",
            )
            if selected_participant_ids:
                st.caption(
                    "Participants: "
                    + ", ".join(_participant_label(agent_id, agent_lookup) for agent_id in selected_participant_ids)
                )
            else:
                st.caption("No participants selected yet.")
            save_participants_col, _ = st.columns([1, 5])
            with save_participants_col:
                if st.button("Save participants", width="content"):
                    try:
                        update_discussion(
                            str(selected_discussion_id),
                            participant_agent_ids=[int(agent_id) for agent_id in selected_participant_ids],
                        )
                    except ApiError as error:
                        st.error(f"Unable to update participants: {error.detail}")
                    else:
                        st.success("Participants updated.")
                        st.rerun()

        with st.container(border=True):
            st.subheader("Group chat")
            mode_labels = {
                "single": "Single agent",
                "round_robin": "Round robin",
                "auto_paced": "Auto paced",
                "continuous": "Continuous loop",
                "direct": "Direct replies",
            }
            mode_options = list(mode_labels.keys())
            try:
                mode_index = mode_options.index(current_chat_mode)
            except ValueError:
                mode_index = 0
            selected_mode = st.selectbox(
                "Mode",
                options=mode_options,
                index=mode_index,
                format_func=lambda mode: mode_labels.get(mode, mode),
                key=f"discussion-chat-mode-{selected_discussion_id}",
            )
            st.caption(MODE_DESCRIPTIONS.get(selected_mode, ""))
            with st.expander("How the modes behave", expanded=False):
                st.markdown(
                    "\n".join(
                        [
                            "- `Single agent`: one agent answers once, then waits for you.",
                            "- `Round robin`: each participant speaks in order, then the room pauses for you.",
                            "- `Auto paced`: the agents continue in order with a configurable delay.",
                            "- `Continuous loop`: the agents continue in order without any pause between turns.",
                            "- `Direct replies`: agents answer whoever they are addressing, and the exchange may end naturally.",
                        ]
                    )
                )
            pause_turns = st.checkbox(
                "Pause between turns",
                value=bool(current_pause_seconds and float(current_pause_seconds) > 0),
                disabled=selected_mode != "auto_paced",
                key=f"discussion-chat-pause-toggle-{selected_discussion_id}",
                help="Only auto-paced mode uses the delay. Turn it off for a continuous loop.",
            )
            pause_seconds = 0.0
            if selected_mode == "auto_paced" and pause_turns:
                pause_seconds = st.number_input(
                    "Pause seconds",
                    min_value=0.0,
                    value=float(current_pause_seconds or 0.0),
                    step=0.5,
                    format="%.1f",
                    key=f"discussion-chat-pause-{selected_discussion_id}",
                )
            coordinator_options = [{"id": None, "name": "No coordinator"}] + agents
            coordinator_index = _selected_index(
                coordinator_options,
                current_coordinator_agent_id,
                "id",
            )
            coordinator = st.selectbox(
                "Coordinator",
                options=coordinator_options,
                index=coordinator_index,
                format_func=lambda option: "No coordinator" if option.get("id") is None else _agent_label(option),
                key=f"discussion-chat-coordinator-{selected_discussion_id}",
            )
            save_col, pause_col, resume_col = st.columns([1, 1, 1])
            with save_col:
                if st.button("Save mode", width="content"):
                    try:
                        set_discussion_group_chat_mode(
                            str(selected_discussion_id),
                            chat_mode=selected_mode,
                            chat_pause_seconds=(
                                pause_seconds
                                if selected_mode == "auto_paced" and pause_turns
                                else 0.0
                                if selected_mode in {"auto_paced", "continuous"}
                                else None
                            ),
                            chat_coordinator_agent_id=coordinator.get("id"),
                        )
                    except ApiError as error:
                        st.error(f"Unable to update group chat mode: {error.detail}")
                    else:
                        st.success(f"Updated group chat mode to {mode_labels.get(selected_mode, selected_mode)}.")
                        st.rerun()
            with pause_col:
                if st.button(
                    "Pause",
                    width="content",
                    disabled=current_chat_mode == "single",
                ):
                    try:
                        pause_group_chat()
                    except ApiError as error:
                        st.error(f"Unable to pause group chat: {error.detail}")
                    else:
                        st.success("Group chat paused.")
                        st.rerun()
            with resume_col:
                if st.button(
                    "Resume",
                    width="content",
                    disabled=current_chat_mode == "single" or not bool(snapshot.get("chat_is_paused")),
                ):
                    try:
                        resume_group_chat()
                    except ApiError as error:
                        st.error(f"Unable to resume group chat: {error.detail}")
                    else:
                        st.success("Group chat resumed.")
                        st.rerun()

    st.divider()
    st.subheader("Messages")
    username = _authenticated_username()
    agent_name = str(selected_agent.get("name") or "Assistant")
    if selected_discussion_id is None:
        st.info("No discussions for this agent yet. Start a new discussion to begin.")
        return
    initial_is_streaming = bool(snapshot.get("is_streaming"))
    is_chat_paused = bool(snapshot.get("chat_is_paused"))
    if initial_is_streaming:
        fragment_factory = getattr(st, "fragment", None)
        if getattr(fragment_factory, "__module__", "").startswith("streamlit"):
            @fragment_factory(run_every=0.5)
            def _streaming_fragment() -> dict[str, object]:
                current_snapshot = _render_streaming_messages(
                    username=username,
                    agent_name=agent_name,
                    agent_lookup=agent_lookup,
                    model_lookup=model_lookup,
                )
                if not (current_snapshot.get("is_streaming") and not current_snapshot.get("chat_is_paused")):
                    st.rerun()
                return current_snapshot

            snapshot = _streaming_fragment()
        else:
            snapshot = _render_streaming_messages(
                username=username,
                agent_name=agent_name,
                agent_lookup=agent_lookup,
                model_lookup=model_lookup,
            )
    else:
        _render_messages(
            snapshot,
            username=username,
            agent_name=agent_name,
            agent_lookup=agent_lookup,
            model_lookup=model_lookup,
        )

    if snapshot.get("last_error"):
        st.error(f"Last error: {snapshot['last_error']}")

    is_streaming = bool(snapshot.get("is_streaming"))
    is_chat_paused = bool(snapshot.get("chat_is_paused"))

    live_activity = snapshot.get("activity") if isinstance(snapshot.get("activity"), dict) else None
    live_llama_status = (
        snapshot.get("llama_server_status") if isinstance(snapshot.get("llama_server_status"), dict) else None
    )
    live_speaker_name = None
    if isinstance(live_activity, dict):
        speaker_name = live_activity.get("speaker_name")
        if speaker_name is not None:
            live_speaker_name = str(speaker_name)
    status_agent_name = live_speaker_name or agent_name
    if is_streaming and not is_chat_paused:
        activity_text = _activity_status_text(
            live_activity,
            agent_lookup=agent_lookup,
            model_lookup=model_lookup,
            llama_server_status=live_llama_status,
        )
        st.caption(activity_text or f"{status_agent_name} is still responding.")
        if st.button("Stop", use_container_width=False):
            try:
                stop_discussion()
            except ApiError as error:
                st.error(f"Unable to stop message: {error.detail}")
                return
            st.success("Message stopped. Refreshing discussion.")
            st.rerun()
    elif is_chat_paused:
        st.info("The group chat is paused. You can send a message now, or resume the conversation later.")

    st.divider()
    prompt_key = f"discussion_prompt_{selected_discussion_id}"
    attachment_key = f"discussion_prompt_attachments_{selected_discussion_id}"
    reset_key = f"discussion_prompt_reset_{selected_discussion_id}"

    if st.session_state.pop(reset_key, False):
        st.session_state.pop(prompt_key, None)
        st.session_state.pop(attachment_key, None)

    if prompt_key not in st.session_state:
        st.session_state[prompt_key] = ""
    with st.form("apmatia_discussion_prompt_form"):
        prompt_placeholder = "Write a message to the selected agent." if not is_chat_paused else "Write a message to continue the paused group chat."
        prompt = st.text_area(
            "Message",
            key=prompt_key,
            height=140,
            placeholder=prompt_placeholder,
            disabled=is_streaming and not is_chat_paused,
        )
        uploaded_files = st.file_uploader(
            "Screenshots or images",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key=attachment_key,
            help="Attach screenshots or other images so the selected model can inspect them. You can also paste images from the clipboard.",
        )
        st.caption("Tip: press Ctrl+V or Cmd+V to paste screenshots directly into the browser.")
        render_clipboard_image_paste_bridge(
            f"discussion-paste-{selected_discussion_id}",
            target_selector='input[type="file"]',
        )
        submitted = st.form_submit_button("Send message", disabled=is_streaming and not is_chat_paused)

    if not submitted:
        return

    if not prompt.strip():
        st.warning("Please enter a message.")
        return

    st.session_state["discussion_selected_agent_id"] = selected_agent.get("id")
    try:
        prompt_discussion(
            prompt=prompt,
            agent_id=int(selected_agent.get("id")),
            attachments=_uploaded_images_to_payload(uploaded_files),
        )
    except ApiError as error:
        st.error(f"Unable to send message: {error.detail}")
        return

    st.session_state[reset_key] = True
    st.success("Message sent. Refreshing discussion.")
    st.rerun()
