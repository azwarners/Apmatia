from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.core.registry import ToolContribution
from apmatia.lib.tool_management.registry import ToolProvider

from .services import ApmatiaIpeService


def ipe_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "whatDoIDo",
            "description": (
                "Return a productivity snapshot for the current user. "
                "Use this to decide the single best next action by considering tasks, habits, calendar pressure, and stale projects."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "current_time": {"type": "string"},
                    "tasks": {"type": "array", "items": {"type": "object"}},
                    "unfinished_habits": {"type": "array", "items": {"type": "object"}},
                    "unfinished_hobbies": {"type": "array", "items": {"type": "object"}},
                    "upcoming_events": {"type": "array", "items": {"type": "object"}},
                    "next_appointment": {"type": ["object", "null"]},
                    "stale_projects": {"type": "array", "items": {"type": "object"}},
                    "suggested_focus": {"type": "string"},
                },
                "required": [
                    "current_time",
                    "tasks",
                    "unfinished_habits",
                    "unfinished_hobbies",
                    "upcoming_events",
                    "stale_projects",
                    "suggested_focus",
                ],
                "additionalProperties": True,
            },
            "provider_id": "builtin.ipe_what_do_i_do",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "ipe"},
        },
    ]


TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="ipe",
        action_id="ipe.what_do_i_do.action",
        tool_id="ipe.what_do_i_do",
        name="whatDoIDo",
        description="Return the current productivity snapshot for the user.",
        metadata={"builtin": True, "library": "ipe"},
    ),
]


@dataclass(slots=True)
class IpeToolProvider:
    provider_id: str
    action: str
    ipe_service: ApmatiaIpeService
    agent_service: AgentService

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if tool_call is None:
            raise ValueError("Tool call context is required.")
        agent = self.agent_service.get_agent(int(tool_call.requester_agent_id))
        if agent is None or agent.id is None:
            raise ValueError(f"Calling agent is unavailable: {tool_call.requester_agent_id}")
        if agent.owner_user_id is None:
            agent = self._restore_agent_owner(agent, tool_call)
        if agent.owner_user_id is None:
            raise ValueError(
                f"Calling agent {agent.id} has no owner_user_id. "
                "Re-save the agent while authenticated, or use it from a discussion owned by a user once so Apmatia can repair it."
            )
        requester_group_ids = {agent.owner_group_id} if agent.owner_group_id is not None else set()

        if self.action == "what_do_i_do":
            return self.ipe_service.what_do_i_do(
                owner_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )

        raise ValueError(f"Unsupported IPE action: {self.action}")

    def _restore_agent_owner(self, agent: Any, tool_call: Any) -> Any:
        discussion_id = getattr(tool_call, "discussion_id", None)
        if not discussion_id:
            return agent
        from apmatia.lib.discussions import discussion_state

        discussion = discussion_state._get_discussion(str(discussion_id))
        if discussion is None or discussion.owner_user_id is None:
            return agent
        try:
            repaired = self.agent_service.update_agent(
                int(agent.id),
                owner_user_id=discussion.owner_user_id,
            )
        except Exception:
            return agent
        return repaired


def build_ipe_tool_providers(
    ipe_service: ApmatiaIpeService,
    agent_service: AgentService,
) -> list[IpeToolProvider]:
    return [
        IpeToolProvider("builtin.ipe_what_do_i_do", "what_do_i_do", ipe_service, agent_service),
    ]
