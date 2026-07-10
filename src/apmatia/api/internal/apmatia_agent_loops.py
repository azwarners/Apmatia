from __future__ import annotations

from typing import Any

from apmatia.modules.apmatia_agent_loops.runner import LoopTaskRequest, get_agent_loop_runner


def start_loop_task(
    *,
    owner_user_id: int,
    contact_kind: str,
    contact_id: int | str,
    title: str,
    prompt: str,
    checklist: list[dict[str, Any]] | None = None,
    participant_agent_ids: list[int] | None = None,
    agent_id: int | None = None,
    chat_mode: str = "single",
    allow_tools: bool = True,
    max_iterations: int = 5,
    member_group_ids: set[int] | None = None,
) -> dict[str, Any]:
    request = LoopTaskRequest(
        owner_user_id=owner_user_id,
        contact_kind=contact_kind,
        contact_id=contact_id,
        title=title,
        prompt=prompt,
        checklist=list(checklist or []),
        participant_agent_ids=list(participant_agent_ids or []),
        agent_id=agent_id,
        chat_mode=chat_mode,
        allow_tools=allow_tools,
        max_iterations=max_iterations,
        member_group_ids=set(member_group_ids or ()),
    )
    return get_agent_loop_runner().start_task(request)


def list_loop_tasks(*, contact_kind: str | None = None, contact_id: int | str | None = None) -> list[dict[str, Any]]:
    return get_agent_loop_runner().list_tasks(contact_kind=contact_kind, contact_id=contact_id)


def get_loop_task(task_id: str) -> dict[str, Any] | None:
    return get_agent_loop_runner().get_task(task_id)


def stop_loop_task(task_id: str) -> dict[str, Any] | None:
    return get_agent_loop_runner().stop_task(task_id)


def wait_for_loop_task(task_id: str, timeout: float | None = None) -> bool:
    return get_agent_loop_runner().wait_for_task(task_id, timeout=timeout)


def get_loop_task_transcript(task_id: str) -> dict[str, Any] | None:
    runner = get_agent_loop_runner()
    task = runner.get_task(task_id)
    if task is None:
        return None
    discussion_id = str(task.get("discussion_id") or "").strip()
    if not discussion_id:
        return {"task_id": task_id, "transcript": None}
    from apmatia.modules.apmatia_agent_loops.prompt_helpers import get_discussion_transcript

    return {
        "task_id": task_id,
        "discussion_id": discussion_id,
        "transcript": get_discussion_transcript(discussion_id),
    }
