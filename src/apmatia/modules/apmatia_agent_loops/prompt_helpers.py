from __future__ import annotations

import threading
from typing import Any

from apmatia.lib.discussions import discussion_state


class _DiscussionStateProxy:
    def __init__(self, *, allow_tools: bool) -> None:
        self._allow_tools = allow_tools

    def __getattr__(self, name: str) -> Any:
        return getattr(discussion_state, name)

    def _list_tools_available_to_agent(self, agent_id: int) -> list[Any]:
        if self._allow_tools:
            return discussion_state._list_tools_available_to_agent(agent_id)  # type: ignore[attr-defined]
        return []


def start_prompt_for_discussion(
    *,
    discussion_id: str,
    prompt: str,
    agent_id: int | None = None,
    attachments: list[dict[str, Any]] | None = None,
    allow_tools: bool = True,
) -> str:
    with discussion_state._lock:  # type: ignore[attr-defined]
        discussion = discussion_state._get_discussion(discussion_id)  # type: ignore[attr-defined]
        if discussion is None:
            raise RuntimeError(f"Discussion not found: {discussion_id}")
        if discussion_id in discussion_state._streaming:  # type: ignore[attr-defined]
            raise RuntimeError("A discussion response is already streaming.")
        discussion_state._record_agent_participation(discussion_id, agent_id)  # type: ignore[attr-defined]
        stored_attachments = discussion_state._store_prompt_attachments(  # type: ignore[attr-defined]
            discussion_id,
            attachments,
        )
        if stored_attachments:
            discussion_state._pending_prompt_attachments[discussion_id] = stored_attachments  # type: ignore[attr-defined]

        stop_event = threading.Event()
        discussion_state._stop_events[discussion_id] = stop_event  # type: ignore[attr-defined]
        discussion_state._streaming.add(discussion_id)  # type: ignore[attr-defined]
        discussion_state._update_discussion(discussion_id, {"last_error": None})  # type: ignore[attr-defined]

        proxy = _DiscussionStateProxy(allow_tools=allow_tools)
        thread = threading.Thread(
            target=type(discussion_state)._run_prompt,  # type: ignore[attr-defined]
            args=(proxy, discussion_id, prompt, agent_id),
            daemon=True,
        )
        discussion_state._threads[discussion_id] = thread  # type: ignore[attr-defined]
        thread.start()
        return discussion_id


def wait_for_prompt_completion(discussion_id: str, timeout: float | None = None) -> bool:
    with discussion_state._lock:  # type: ignore[attr-defined]
        thread = discussion_state._threads.get(discussion_id)  # type: ignore[attr-defined]
    if thread is None:
        return True
    thread.join(timeout=timeout)
    return not thread.is_alive()


def stop_prompt_for_discussion(discussion_id: str) -> bool:
    with discussion_state._lock:  # type: ignore[attr-defined]
        stop_event = discussion_state._stop_events.get(discussion_id)  # type: ignore[attr-defined]
        if stop_event is None or discussion_id not in discussion_state._streaming:  # type: ignore[attr-defined]
            return False
        stop_event.set()
        return True


def get_discussion_transcript(discussion_id: str) -> dict[str, Any]:
    discussion = discussion_state._get_discussion(discussion_id)  # type: ignore[attr-defined]
    if discussion is None:
        raise ValueError(f"Discussion not found: {discussion_id}")
    path = discussion_state._discussion_path(discussion_id)  # type: ignore[attr-defined]
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    messages = discussion_state._parse_messages(content)  # type: ignore[attr-defined]
    messages = [discussion_state._hydrate_message_attachments(discussion_id, message) for message in messages]  # type: ignore[attr-defined]
    return {
        "discussion": discussion_state._discussion_to_public_dict(discussion),  # type: ignore[attr-defined]
        "discussion_id": discussion_id,
        "content": content,
        "messages": messages,
    }


def build_loop_task_prompt(
    *,
    title: str,
    contact_kind: str,
    contact_id: int | str,
    workspace_root: str,
    knowledge_root: str,
    prompt: str,
    checklist_text: str,
    allow_tools: bool,
) -> str:
    tool_policy = "You may use tools when they help complete the task." if allow_tools else "Do not use tools."
    return (
        f"{prompt}\n\n"
        "You are running inside the Apmatia Agent Loops module.\n"
        f"Task title: {title}\n"
        f"Contact kind: {contact_kind}\n"
        f"Contact id: {contact_id}\n"
        f"Workspace root: {workspace_root}\n"
        f"Knowledge root: {knowledge_root}\n"
        f"Checklist:\n{checklist_text}\n\n"
        f"{tool_policy}\n"
        "If the task creates or updates agents, use the list_agents tool to confirm the requested agents exist "
        "before you mark that checklist item complete.\n"
        "Keep working until the task is complete.\n"
        "At the end of your response, include a <loop_status> JSON block with keys:\n"
        '"done" (boolean), "summary" (string), "completed_items" (array), '
        '"remaining_items" (array), "next_action" (string), and "executive_analysis" (string).\n'
        "If the task is complete, set done to true and make the executive_analysis user-facing."
    ).strip()


def build_loop_followup_prompt(
    *,
    title: str,
    remaining_items_text: str,
) -> str:
    return (
        f"Continue the same task for {title}.\n"
        "Review the current transcript, work on the next highest-value item, and keep going until done.\n"
        f"Remaining items:\n{remaining_items_text}\n\n"
        "End with an updated <loop_status> JSON block using the same keys as before."
    ).strip()


def parse_checklist_text(value: str) -> list[dict[str, Any]]:
    checklist: list[dict[str, Any]] = []
    for line in str(value or "").splitlines():
        text = line.strip()
        if text:
            checklist.append({"label": text})
    return checklist
