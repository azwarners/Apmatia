from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management.registry import ToolProvider


def agent_loop_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_agents",
            "description": (
                "List the current agents so a loop can verify that requested agents were actually created."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name_contains": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "agents": {"type": "array"},
                },
                "required": ["agents"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.agent_loops_list_agents",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "module": "apmatia_agent_loops"},
        }
    ]


@dataclass(slots=True)
class AgentLoopToolProvider:
    provider_id: str
    action: str
    agent_service: AgentService

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if self.action != "list_agents":
            raise ValueError(f"Unsupported agent loop tool action: {self.action}")
        name_contains = str(arguments.get("name_contains") or "").strip().lower()
        agents: list[dict[str, Any]] = []
        for agent in self.agent_service.list_agents():
            name = str(getattr(agent, "name", "") or f"Agent {getattr(agent, 'id', '')}")
            if name_contains and name_contains not in name.lower():
                continue
            agents.append(
                {
                    "id": getattr(agent, "id", None),
                    "name": name,
                    "owner_user_id": getattr(agent, "owner_user_id", None),
                    "owner_group_id": getattr(agent, "owner_group_id", None),
                    "active_model_id": getattr(agent, "active_model_id", None),
                    "default_model_id": getattr(agent, "default_model_id", None),
                }
            )
        return {"agents": agents}


def build_agent_loop_tool_providers(agent_service: AgentService) -> list[ToolProvider]:
    return [
        AgentLoopToolProvider(
            provider_id="builtin.agent_loops_list_agents",
            action="list_agents",
            agent_service=agent_service,
        )
    ]
