from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .manager import MemoryManager
from .models import MemoryItem


class ApmatiaMemoryManagerModuleViewProvider:
    def __init__(
        self,
        manager: MemoryManager | None = None,
        manager_factory: Callable[[], MemoryManager] | None = None,
        agent_manager: Any | None = None,
        agent_manager_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._manager = manager
        self._manager_factory = manager_factory
        self._agent_manager = agent_manager
        self._agent_manager_factory = agent_manager_factory

    @property
    def manager(self) -> MemoryManager:
        if self._manager is None:
            if self._manager_factory is None:
                raise ValueError("Memory manager module view provider is missing a manager factory.")
            self._manager = self._manager_factory()
        return self._manager

    @property
    def agent_manager(self) -> Any:
        if self._agent_manager is None:
            if self._agent_manager_factory is None:
                raise ValueError("Memory manager module view provider is missing an agent manager factory.")
            self._agent_manager = self._agent_manager_factory()
        return self._agent_manager

    def list_items(self, *, view: ViewContribution, context: ModuleViewContext) -> list[dict[str, Any]]:
        del view
        memories = self.manager.list_memories(
            requester_user_id=context.user_id,
            requester_group_ids=set(context.group_ids),
            include_archived=True,
        )
        return [_serialize_memory(memory) for memory in memories]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        verb = str(command.metadata.get("verb") or command.command_id.rsplit(".", 1)[-1]).strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb == "create":
            memory = self.manager.create_memory(
                str(payload.get("title") or "").strip(),
                str(payload.get("content") or ""),
                owner_user_id=context.user_id,
                owner_agent_id=self._validated_owner_agent_id(payload.get("owner_agent_id"), context=context),
                tags=_parse_list(payload.get("tags")),
                visibility=str(payload.get("visibility") or "draft"),
                source_discussion_id=_optional_string(payload.get("source_discussion_id")),
                source_message_ids=_parse_list(payload.get("source_message_ids")),
            )
            return {"status": "created", "item": _serialize_memory(memory)}

        memory_id = _required_int(payload.get("item_id"))
        if verb == "edit":
            updates = {
                "title": str(payload.get("title") or "").strip(),
                "content": str(payload.get("content") or ""),
                "tags": _parse_list(payload.get("tags")),
                "owner_agent_id": self._validated_owner_agent_id(payload.get("owner_agent_id"), context=context),
                "visibility": str(payload.get("visibility") or "draft"),
                "status": str(payload.get("status") or "active"),
                "source_discussion_id": _optional_string(payload.get("source_discussion_id")),
                "source_message_ids": _parse_list(payload.get("source_message_ids")),
            }
            memory = self.manager.update_memory(
                memory_id,
                requester_user_id=context.user_id,
                requester_group_ids=set(context.group_ids),
                **updates,
            )
            return {"status": "updated", "item": _serialize_memory(memory)}
        if verb == "delete":
            memory = self.manager.delete_memory(
                memory_id,
                requester_user_id=context.user_id,
                requester_group_ids=set(context.group_ids),
            )
            return {"status": "deleted", "item_id": memory_id, "deleted": True, "item": _serialize_memory(memory)}
        raise ValueError(f"Unsupported memory manager command verb: {verb}")

    def _validated_owner_agent_id(self, value: Any, *, context: ModuleViewContext) -> int | None:
        agent_id = _optional_int(value)
        if agent_id is None:
            return None
        agent = self.agent_manager.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        if agent.owner_user_id == context.user_id:
            return agent_id
        if agent.owner_user_id is None and agent.owner_group_id is None:
            return agent_id
        raise PermissionError(f"You cannot assign memories to agent {agent_id}.")


def _serialize_memory(memory: MemoryItem) -> dict[str, Any]:
    return {
        "id": memory.id,
        "title": memory.title,
        "content": memory.content,
        "tags": list(memory.tags),
        "owner_agent_id": memory.owner_agent_id,
        "visibility": memory.visibility,
        "status": memory.status,
        "source_discussion_id": memory.source_discussion_id,
        "source_message_ids": list(memory.source_message_ids),
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
    }


def _parse_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return _required_int(value)


def _required_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid memory ID is required.") from error


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _view_from_command(command: CommandContribution) -> ViewContribution:
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=str(command.metadata.get("collection_view_id") or ""),
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )
