from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.modules.memory_manager.services import MemoryService


def memory_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "memory_create",
            "description": "Persist a memory item for the calling agent.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "visibility": {"type": "string"},
                    "source_discussion_id": {"type": "string"},
                    "source_message_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer"},
                    "id": {"type": "integer"},
                    "owner_agent_id": {"type": ["integer", "null"]},
                    "status": {"type": "string"},
                    "visibility": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["memory_id", "status", "visibility", "title"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.memory_create",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "memory_search",
            "description": "Search the calling agent's visible memories by text.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "include_archived": {"type": "boolean"},
                    "source_discussion_id": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "memories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "title": {"type": "string"},
                                "owner_agent_id": {"type": ["integer", "null"]},
                                "status": {"type": "string"},
                                "visibility": {"type": "string"},
                            },
                            "required": ["id", "title", "status", "visibility"],
                            "additionalProperties": True,
                        },
                    },
                },
                "required": ["count", "memories"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.memory_search",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True},
        },
        {
            "name": "memory_get",
            "description": "Retrieve a persisted memory item by id.",
            "input_schema": {
                "type": "object",
                "properties": {"memory_id": {"type": "integer"}},
                "required": ["memory_id"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "memory": {"type": "object"},
                },
                "required": ["memory"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.memory_get",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True},
        },
        {
            "name": "memory_update",
            "description": "Update a persisted memory item owned by the calling agent.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "visibility": {"type": "string"},
                    "source_discussion_id": {"type": "string"},
                    "source_message_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["memory_id"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer"},
                    "id": {"type": "integer"},
                    "owner_agent_id": {"type": ["integer", "null"]},
                    "status": {"type": "string"},
                    "visibility": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["memory_id", "status", "visibility", "title"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.memory_update",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "memory_archive",
            "description": "Archive a persisted memory item owned by the calling agent.",
            "input_schema": {
                "type": "object",
                "properties": {"memory_id": {"type": "integer"}},
                "required": ["memory_id"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer"},
                    "status": {"type": "string"},
                },
                "required": ["memory_id", "status"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.memory_archive",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
    ]


@dataclass(slots=True)
class MemoryToolProvider:
    provider_id: str
    action: str
    memory_service: MemoryService
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

        if self.action == "create":
            memory = self.memory_service.create_memory(
                title=str(arguments["title"]),
                content=str(arguments["content"]),
                tags=list(arguments.get("tags", [])),
                visibility=str(arguments.get("visibility", "draft")),
                owner_user_id=agent.owner_user_id,
                owner_group_id=agent.owner_group_id,
                owner_agent_id=int(agent.id),
                created_by_agent_id=int(agent.id),
                source_discussion_id=arguments.get("source_discussion_id"),
                source_message_ids=list(arguments.get("source_message_ids", [])),
            )
            return _memory_summary(memory)

        memory_id = int(arguments["memory_id"]) if "memory_id" in arguments else None

        if self.action == "get":
            memory = self.memory_service.get_memory(
                int(memory_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )
            if memory is None or not _belongs_to_agent(memory, int(agent.id)):
                raise ValueError(f"Memory not found: {memory_id}")
            return {"memory": _memory_detail(memory)}

        if self.action == "search":
            memories = self.memory_service.search_memories(
                str(arguments.get("query", "")),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                owner_user_id=agent.owner_user_id,
                include_archived=bool(arguments.get("include_archived", False)),
                limit=int(arguments["limit"]) if arguments.get("limit") is not None else 50,
            )
            memories = [memory for memory in memories if _belongs_to_agent(memory, int(agent.id))]
            return {
                "count": len(memories),
                "memories": [_memory_summary(memory) for memory in memories],
            }

        if self.action == "update":
            existing = self.memory_service.get_memory(
                int(memory_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )
            if existing is None or not _belongs_to_agent(existing, int(agent.id)):
                raise ValueError(f"Memory not found: {memory_id}")
            updates: dict[str, Any] = {}
            for field in (
                "title",
                "content",
                "tags",
                "visibility",
                "source_discussion_id",
                "source_message_ids",
            ):
                if field in arguments:
                    updates[field] = arguments[field]
            memory = self.memory_service.update_memory(
                int(memory_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                owner_agent_id=int(agent.id),
                **updates,
            )
            return _memory_summary(memory)

        if self.action == "archive":
            existing = self.memory_service.get_memory(
                int(memory_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )
            if existing is None or not _belongs_to_agent(existing, int(agent.id)):
                raise ValueError(f"Memory not found: {memory_id}")
            memory = self.memory_service.archive_memory(
                int(memory_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )
            return {"memory_id": int(memory.id), "status": memory.status}

        raise ValueError(f"Unsupported memory action: {self.action}")

    def _restore_agent_owner(self, agent: Any, tool_call: Any) -> Any:
        discussion_id = getattr(tool_call, "discussion_id", None)
        if not discussion_id:
            return agent
        from apmatia.modules.contacts_and_discussions.services import get_discussion as _get_discussion

        discussion = _get_discussion(discussion_id)
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


def build_memory_tool_providers(
    memory_service: MemoryService,
    agent_service: AgentService,
) -> list[MemoryToolProvider]:
    return [
        MemoryToolProvider("builtin.memory_create", "create", memory_service, agent_service),
        MemoryToolProvider("builtin.memory_search", "search", memory_service, agent_service),
        MemoryToolProvider("builtin.memory_get", "get", memory_service, agent_service),
        MemoryToolProvider("builtin.memory_update", "update", memory_service, agent_service),
        MemoryToolProvider("builtin.memory_archive", "archive", memory_service, agent_service),
    ]


def _memory_summary(memory) -> dict[str, Any]:
    return {
        "memory_id": int(memory.id),
        "id": int(memory.id),
        "title": memory.title,
        "owner_agent_id": memory.owner_agent_id,
        "status": memory.status,
        "visibility": memory.visibility,
    }


def _memory_detail(memory) -> dict[str, Any]:
    return {
        "id": int(memory.id),
        "title": memory.title,
        "content": memory.content,
        "tags": list(memory.tags),
        "owner_user_id": memory.owner_user_id,
        "owner_group_id": memory.owner_group_id,
        "owner_agent_id": memory.owner_agent_id,
        "mode": memory.mode,
        "created_by_agent_id": memory.created_by_agent_id,
        "source_discussion_id": memory.source_discussion_id,
        "source_message_ids": list(memory.source_message_ids),
        "visibility": memory.visibility,
        "status": memory.status,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
    }


def _belongs_to_agent(memory: Any, agent_id: int) -> bool:
    owner_agent_id = getattr(memory, "owner_agent_id", None)
    created_by_agent_id = getattr(memory, "created_by_agent_id", None)
    return owner_agent_id == agent_id or (owner_agent_id is None and created_by_agent_id == agent_id)
