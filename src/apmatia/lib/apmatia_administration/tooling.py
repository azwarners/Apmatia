from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management.registry import ToolProvider

DEFAULT_AGENT_MODE = 0o600


_AGENT_PROMPT_PROPERTIES: dict[str, dict[str, Any]] = {
    "personality": {"type": "string"},
    "skills": {"type": "string"},
    "purpose": {"type": "string"},
    "backstory": {"type": "string"},
    "communication_style": {"type": "string"},
    "operating_principles": {"type": "string"},
    "autonomy_level": {"type": "string"},
    "decision_making_style": {"type": "string"},
    "memory_policy": {"type": "string"},
    "domain_priorities": {"type": "string"},
    "relationship_to_user": {"type": "string"},
    "tool_use_policy": {"type": "string"},
    "capability_boundaries": {"type": "string"},
    "output_preferences": {"type": "string"},
    "safety_ethics": {"type": "string"},
    "selfhood_truthfulness": {"type": "string"},
    "conflict_resolution_rules": {"type": "string"},
    "use_raw_prompt_override": {"type": "boolean"},
    "raw_prompt_override": {"type": "string"},
}


def apmatia_administration_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "apmatia_create_agent",
            "description": (
                "Create a new Apmatia agent with a full prompt configuration. "
                "Use this to define the agent's name, ownership, and all prompt fields in one step."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "owner_user_id": {"type": "integer"},
                    "owner_group_id": {"type": "integer"},
                    "mode": {"type": "integer"},
                    "system_prompt_id": {"type": "integer"},
                    "memory_id": {"type": "integer"},
                    "rag_root_ids": {"type": "array", "items": {"type": "integer"}},
                    "tool_ids": {"type": "array", "items": {"type": "integer"}},
                    "default_model_id": {"type": "integer"},
                    "active_model_id": {"type": "integer"},
                    "workspace_root": {"type": "string"},
                    "knowledge_root": {"type": "string"},
                    "metadata": {"type": "object"},
                    **_AGENT_PROMPT_PROPERTIES,
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "object"},
                },
                "required": ["agent"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.apmatia_create_agent",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "library": "apmatia_administration"},
        },
        {
            "name": "clone_agent_as",
            "description": (
                "Clone an existing Apmatia agent into a new name while preserving ownership, "
                "prompt configuration, memory access, and tool wiring."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "source_agent_id": {"type": "integer"},
                    "name": {"type": "string"},
                },
                "required": ["source_agent_id", "name"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "object"},
                },
                "required": ["agent"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.apmatia_clone_agent_as",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "library": "apmatia_administration"},
        },
        {
            "name": "set_agent_mode",
            "description": (
                "Switch the current discussion between discussion mode and agentic mode. "
                "Agentic mode enables gentle nudges after tool calls so the agent can keep working autonomously."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["discussion", "agentic"],
                    },
                },
                "required": ["mode"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "previous_mode": {"type": "string"},
                    "current_mode": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["previous_mode", "current_mode", "status"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.apmatia_set_agent_mode",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "library": "apmatia_administration"},
        },
    ]


@dataclass(slots=True)
class ApmatiaAdministrationToolProvider:
    provider_id: str
    action: str
    agent_service: AgentService

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if tool_call is None:
            raise ValueError("Tool call context is required.")

        agent = self.agent_service.get_agent(int(tool_call.requester_agent_id))
        if agent is None or agent.id is None:
            raise ValueError(f"Calling agent is unavailable: {tool_call.requester_agent_id}")
        owner_user_id, owner_group_id = _resolve_owner_context(agent, arguments, tool_call)
        if owner_user_id is None:
            raise ValueError(
                f"Calling agent {agent.id} has no owner_user_id. "
                "Re-save the agent while authenticated before using the administration tools."
            )

        if self.action == "create_agent":
            prompt_kwargs = _collect_prompt_kwargs(arguments)
            created_agent = self.agent_service.create_agent(
                str(arguments["name"]),
                owner_user_id=owner_user_id,
                owner_group_id=owner_group_id,
                mode=_resolve_mode(arguments, agent),
                system_prompt_id=arguments.get("system_prompt_id", getattr(agent, "system_prompt_id", 0)),
                memory_id=arguments.get("memory_id", getattr(agent, "memory_id", 0)),
                rag_root_ids=list(arguments.get("rag_root_ids", [])),
                tool_ids=list(arguments.get("tool_ids", [])),
                default_model_id=arguments.get("default_model_id", getattr(agent, "default_model_id", None)),
                active_model_id=arguments.get("active_model_id", getattr(agent, "active_model_id", None)),
                workspace_root=arguments.get("workspace_root", getattr(agent, "workspace_root", "")),
                knowledge_root=arguments.get("knowledge_root", getattr(agent, "knowledge_root", "")),
                metadata=dict(arguments.get("metadata", getattr(agent, "metadata", {}))),
                **prompt_kwargs,
            )
            return {
                "agent": _agent_summary(created_agent),
            }

        if self.action == "clone_agent":
            source_agent_id = _coerce_optional_int(arguments.get("source_agent_id"))
            if source_agent_id is None:
                raise ValueError("source_agent_id is required.")
            source_agent = self.agent_service.get_agent(source_agent_id)
            if source_agent is None:
                raise ValueError(f"Source agent not found: {source_agent_id}")
            cloned_agent = self.agent_service.clone_agent(
                source_agent_id,
                str(arguments["name"]),
            )
            return {
                "agent": _agent_summary(cloned_agent),
            }

        if self.action == "set_agent_mode":
            from apmatia.modules.contacts_and_discussions.services import set_agent_mode as _set_agent_mode

            discussion_id = str(getattr(tool_call, "discussion_id", "") or "").strip()
            if not discussion_id:
                raise ValueError("Tool call discussion_id is required.")
            requested_mode = str(arguments.get("mode", "")).strip().lower()
            if requested_mode not in {"discussion", "agentic"}:
                raise ValueError("mode must be either 'discussion' or 'agentic'.")

            refreshed = _set_agent_mode(discussion_id=discussion_id, mode=requested_mode)
            return {
                "previous_mode": str(refreshed.get("previous_mode") or "discussion"),
                "current_mode": str(refreshed.get("current_mode") or requested_mode),
                "status": str(refreshed.get("status") or "updated"),
            }

        raise ValueError(f"Unsupported administration action: {self.action}")


def build_apmatia_administration_tool_providers(agent_service: AgentService) -> list[ToolProvider]:
    return [
        ApmatiaAdministrationToolProvider(
            provider_id="builtin.apmatia_create_agent",
            action="create_agent",
            agent_service=agent_service,
        ),
        ApmatiaAdministrationToolProvider(
            provider_id="builtin.apmatia_clone_agent_as",
            action="clone_agent",
            agent_service=agent_service,
        ),
        ApmatiaAdministrationToolProvider(
            provider_id="builtin.apmatia_set_agent_mode",
            action="set_agent_mode",
            agent_service=agent_service,
        ),
    ]


def _collect_prompt_kwargs(arguments: dict[str, Any]) -> dict[str, Any]:
    prompt_kwargs: dict[str, Any] = {}
    for field in _AGENT_PROMPT_PROPERTIES:
        if field in arguments:
            prompt_kwargs[field] = arguments[field]
    if prompt_kwargs:
        return prompt_kwargs
    return {}


def _resolve_mode(arguments: dict[str, Any], agent: Any) -> int:
    if "mode" in arguments and arguments["mode"] is not None:
        return int(arguments["mode"])
    inherited_mode = getattr(agent, "mode", None)
    if inherited_mode in (None, 0):
        return DEFAULT_AGENT_MODE
    return int(inherited_mode) | 0o200


def _resolve_owner_context(agent: Any, arguments: dict[str, Any], tool_call: Any) -> tuple[int | None, int | None]:
    owner_user_id = _coerce_optional_int(arguments.get("owner_user_id"))
    owner_group_id = _coerce_optional_int(arguments.get("owner_group_id"))

    if owner_user_id is None:
        owner_user_id = _coerce_optional_int(getattr(agent, "owner_user_id", None))
    if owner_group_id is None:
        owner_group_id = _coerce_optional_int(getattr(agent, "owner_group_id", None))

    if (owner_user_id is None or owner_group_id is None) and getattr(tool_call, "discussion_id", None):
        try:
            from apmatia.modules.contacts_and_discussions.services import get_discussion as _get_discussion

            discussion = _get_discussion(tool_call.discussion_id)
        except Exception:
            discussion = None
        if discussion is not None:
            if owner_user_id is None:
                owner_user_id = _coerce_optional_int(getattr(discussion, "owner_user_id", None))
            if owner_group_id is None:
                owner_group_id = _coerce_optional_int(getattr(discussion, "owner_group_id", None))
            if owner_group_id is None:
                owner_group_id = _coerce_optional_int(getattr(discussion, "group_id", None))

    return owner_user_id, owner_group_id


def _agent_summary(agent: Any) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "owner_user_id": getattr(agent, "owner_user_id", None),
        "owner_group_id": getattr(agent, "owner_group_id", None),
        "mode": getattr(agent, "mode", None),
        "prompt_id": agent.prompt_id,
        "system_prompt_id": agent.system_prompt_id,
        "memory_id": agent.memory_id,
        "rag_root_ids": agent.rag_root_ids,
        "tool_ids": agent.tool_ids,
        "default_model_id": agent.default_model_id,
        "active_model_id": agent.active_model_id,
        "workspace_root": getattr(agent, "workspace_root", ""),
        "knowledge_root": getattr(agent, "knowledge_root", ""),
        "metadata": agent.metadata,
    }


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
