from __future__ import annotations

from typing import Any

from apmatia.modules.agents.runtime import get_agent_manager
from apmatia.modules.agent_loops.runner import LoopTaskRequest, get_agent_loop_runner


class LoopTaskAccessError(PermissionError):
    """Raised when a user cannot access an agent-loop task."""


def _has_owner_access(item: Any, *, user_id: int, group_ids: set[int]) -> bool:
    owner_user_id = getattr(item, "owner_user_id", None)
    owner_group_id = getattr(item, "owner_group_id", None)
    return owner_user_id == user_id or (
        owner_group_id is not None and owner_group_id in group_ids
    )


def _is_conversation_task(task: dict[str, Any]) -> bool:
    return str(task.get("chat_mode") or "").strip().lower() == "conversation"


def _task_or_error(task_id: str, *, user_id: int, group_ids: set[int]) -> dict[str, Any]:
    task = get_agent_loop_runner().get_task(task_id)
    if task is None:
        raise KeyError(f"Task not found: {task_id}")
    if not _is_conversation_task(task):
        raise KeyError(f"Conversation task not found: {task_id}")
    if not _has_owner_access_dict(task, user_id=user_id, group_ids=group_ids):
        raise LoopTaskAccessError(f"Task access denied: {task_id}")
    return task


def _has_owner_access_dict(item: dict[str, Any], *, user_id: int, group_ids: set[int]) -> bool:
    owner_user_id = item.get("owner_user_id")
    owner_group_id = item.get("owner_group_id")
    return owner_user_id == user_id or (
        owner_group_id is not None and owner_group_id in group_ids
    )


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
    max_iterations: int = 10,
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
    return get_agent_loop_runner().get_task_transcript(task_id)


def create_conversation_task(
    *, user_id: int, group_ids: set[int], agent_id: int, title: str = ""
) -> dict[str, Any]:
    agent = get_agent_manager().get_agent(int(agent_id))
    if agent is None:
        raise KeyError(f"Agent not found: {agent_id}")
    if not _has_owner_access(agent, user_id=user_id, group_ids=group_ids):
        raise LoopTaskAccessError(f"Agent access denied: {agent_id}")
    return get_agent_loop_runner().create_task(
        agent_id=int(agent_id),
        owner_user_id=user_id,
        owner_group_id=getattr(agent, "owner_group_id", None),
        title=title,
    )


def list_conversation_tasks(*, user_id: int, group_ids: set[int], agent_id: int) -> list[dict[str, Any]]:
    agent = get_agent_manager().get_agent(int(agent_id))
    if agent is None:
        raise KeyError(f"Agent not found: {agent_id}")
    if not _has_owner_access(agent, user_id=user_id, group_ids=group_ids):
        raise LoopTaskAccessError(f"Agent access denied: {agent_id}")
    return [
        task
        for task in get_agent_loop_runner().list_tasks(
            contact_kind="agent", contact_id=agent_id
        )
        if _has_owner_access_dict(task, user_id=user_id, group_ids=group_ids)
        and _is_conversation_task(task)
    ]


def get_conversation_task(*, task_id: str, user_id: int, group_ids: set[int]) -> dict[str, Any]:
    return _task_or_error(task_id, user_id=user_id, group_ids=group_ids)


def submit_conversation_message(
    *, task_id: str, text: str, user_id: int, group_ids: set[int]
) -> dict[str, Any]:
    _task_or_error(task_id, user_id=user_id, group_ids=group_ids)
    return get_agent_loop_runner().submit_message(task_id, text)


def stop_conversation_task(*, task_id: str, user_id: int, group_ids: set[int]) -> dict[str, Any] | None:
    _task_or_error(task_id, user_id=user_id, group_ids=group_ids)
    return get_agent_loop_runner().stop_task(task_id)


def archive_conversation_task(*, task_id: str, user_id: int, group_ids: set[int]) -> dict[str, Any] | None:
    _task_or_error(task_id, user_id=user_id, group_ids=group_ids)
    return get_agent_loop_runner().archive_task(task_id)


def decide_conversation_approval(
    *, task_id: str, decision: str, user_id: int, group_ids: set[int]
) -> dict[str, Any] | None:
    _task_or_error(task_id, user_id=user_id, group_ids=group_ids)
    return get_agent_loop_runner().decide_approval(task_id, decision)
