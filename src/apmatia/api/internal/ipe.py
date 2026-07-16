from __future__ import annotations

from apmatia.api.internal.agent_management import _agent_to_dict
from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.ipe_runtime import get_ipe_service
from apmatia.core.tool_management_runtime import get_tool_manager


def ensure_ipe_coach_agent_for_user(user_id: int, *, username: str | None = None) -> dict:
    agent_manager = get_agent_manager()
    tool_manager = get_tool_manager()
    ipe_service = get_ipe_service()

    tool_id = _ipe_what_do_i_do_tool_id(tool_manager)
    agent = ipe_service.ensure_ipe_coach_agent(
        agent_service=agent_manager,
        owner_user_id=int(user_id),
        agent_name=_coach_name(user_id, username=username),
        tool_ids=[] if tool_id is None else [tool_id],
    )
    return _agent_to_dict(agent)


def _ipe_what_do_i_do_tool_id(tool_manager) -> int | None:
    for tool in tool_manager.list_tool_definitions():
        if getattr(tool, "provider_id", None) == "builtin.ipe_what_do_i_do":
            tool_id = getattr(tool, "id", None)
            return None if tool_id is None else int(tool_id)
    return None


def _coach_name(user_id: int, *, username: str | None = None) -> str:
    label = (username or "").strip()
    if label:
        return f"{label} IPE Coach"
    return f"Apmatia IPE Coach {int(user_id)}"
