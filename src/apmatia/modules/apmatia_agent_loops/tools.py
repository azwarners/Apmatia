from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management.registry import FunctionTool

from .models import ToolDefinition


def agent_loop_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_agents",
            "description": "Return the agents available to the loop.",
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
                    "agents": {
                        "type": "array",
                        "items": {"type": "object"},
                    }
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


def build_agent_loop_tool_providers(agent_service: AgentService) -> list[FunctionTool]:
    return [FunctionTool("builtin.agent_loops_list_agents", _ListAgentsTool(agent_service).execute)]


class _ListAgentsTool:
    def __init__(self, agent_service: AgentService) -> None:
        self._agent_service = agent_service

    def execute(self, *, name_contains: str | None = None) -> dict[str, Any]:
        agents = self._agent_service.list_agents()
        needle = str(name_contains or "").strip().lower()
        if needle:
            agents = [agent for agent in agents if needle in str(agent.name).lower()]
        return {
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "owner_user_id": agent.owner_user_id,
                    "owner_group_id": agent.owner_group_id,
                    "tool_ids": list(agent.tool_ids),
                }
                for agent in agents
            ]
        }


ToolExecutorDefinition = ToolDefinition
