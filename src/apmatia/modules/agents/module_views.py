from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.core.permissions import can_write

from .manager import DEFAULT_AGENT_MODE, AgentManager
from .models import Agent


class AgentsModuleViewProvider:
    """Registry-backed API surface for the stable Agents view."""

    def __init__(self, *, manager_factory: Callable[[], AgentManager]) -> None:
        self._manager_factory = manager_factory

    @property
    def manager(self) -> AgentManager:
        return self._manager_factory()

    def list_items(self, *, view: ViewContribution, context: ModuleViewContext) -> list[dict[str, Any]]:
        del view
        return [_serialize_agent(agent) for agent in self.manager.list_agents() if _is_visible(agent, context)]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        user_id = _require_authenticated_user(context)
        verb = str(command.metadata.get("verb") or command.command_id.rsplit(".", 1)[-1]).strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb == "create":
            values = _agent_values(payload)
            values["owner_user_id"] = user_id
            values["mode"] = DEFAULT_AGENT_MODE
            agent = self.manager.create_agent(str(payload.get("name") or ""), **values)
            return {"status": "created", "item": _serialize_agent(agent)}

        agent_id = _required_int(payload.get("item_id", payload.get("agent_id")), label="agent ID")
        agent = self.manager.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        _require_write_access(agent, context)
        if verb == "edit":
            agent = self.manager.update_agent(agent_id, **_agent_values(payload, include_name=True))
            return {"status": "updated", "item": _serialize_agent(agent)}
        if verb == "delete":
            deleted = self.manager.delete_agent(agent_id)
            return {"status": "deleted" if deleted else "not_found", "deleted": bool(deleted)}
        raise ValueError(f"Unsupported agents command verb: {verb}")


def _agent_values(payload: Mapping[str, Any], *, include_name: bool = False) -> dict[str, Any]:
    keys = {
        "prompt_id",
        "system_prompt_id",
        "memory_id",
        "rag_root_ids",
        "tool_ids",
        "default_model_id",
        "active_model_id",
        "workspace_root",
        "knowledge_root",
        "metadata",
    }
    if include_name:
        keys.update(("name", "owner_user_id", "owner_group_id"))
    return {key: payload[key] for key in keys if key in payload}


def _is_visible(agent: Agent, context: ModuleViewContext) -> bool:
    if context.user_id is None:
        return not context.group_ids
    if agent.owner_user_id == context.user_id:
        return True
    return agent.owner_group_id is not None and agent.owner_group_id in context.group_ids


def _require_write_access(agent: Agent, context: ModuleViewContext) -> None:
    user_id = _require_authenticated_user(context)
    group_ids = set(context.group_ids)
    if can_write(agent, user_id, group_ids):
        return
    if agent.owner_user_id == user_id:
        return
    if agent.owner_group_id is not None and agent.owner_group_id in group_ids:
        return
    raise ValueError("Agent access denied.")


def _serialize_agent(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "owner_user_id": agent.owner_user_id,
        "owner_group_id": agent.owner_group_id,
        "prompt_id": agent.prompt_id,
        "system_prompt_id": agent.system_prompt_id,
        "memory_id": agent.memory_id,
        "rag_root_ids": list(agent.rag_root_ids),
        "tool_ids": list(agent.tool_ids),
        "default_model_id": agent.default_model_id,
        "active_model_id": agent.active_model_id,
        "workspace_root": agent.workspace_root,
        "knowledge_root": agent.knowledge_root,
        "metadata": dict(agent.metadata),
    }


def _require_authenticated_user(context: ModuleViewContext) -> int:
    if context.user_id is None:
        raise ValueError("Authentication required.")
    return int(context.user_id)


def _required_int(value: Any, *, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"A valid {label} is required.") from error


def _view_from_command(command: CommandContribution) -> ViewContribution:
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=str(command.metadata.get("collection_view_id") or ""),
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )
