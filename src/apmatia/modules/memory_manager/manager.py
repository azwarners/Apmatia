from __future__ import annotations

from dataclasses import replace

from apmatia.core.models import utc_now
from apmatia.core.permissions import can_read, can_write

from .models import MemoryItem
from .repositories import MemoryRepository
from .services import MemoryService


class MemoryManager(MemoryService):
    def __init__(self, memory_repo: MemoryRepository):
        self._memory_repo = memory_repo

    def create_memory(self, title: str, content: str, **kwargs) -> MemoryItem:
        memory = MemoryItem(
            id=None,
            owner_user_id=kwargs.get("owner_user_id"),
            owner_group_id=kwargs.get("owner_group_id"),
            owner_agent_id=kwargs.get("owner_agent_id"),
            mode=kwargs.get("mode", 0o000),
            title=title,
            content=content,
            tags=list(kwargs.get("tags", [])),
            created_by_agent_id=kwargs.get("created_by_agent_id"),
            source_discussion_id=kwargs.get("source_discussion_id"),
            source_message_ids=list(kwargs.get("source_message_ids", [])),
            visibility=kwargs.get("visibility", "draft"),
            status=kwargs.get("status", "active"),
        )
        memory_id = self._memory_repo.create(memory)
        return replace(memory, id=memory_id)

    def get_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        include_deleted: bool = False,
    ) -> MemoryItem | None:
        memory = self._memory_repo.get(memory_id)
        if memory is None:
            return None
        if memory.status == "deleted" and not include_deleted:
            return None
        if not self._can_view(memory, requester_user_id, requester_group_ids or set()):
            return None
        return memory

    def update_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        **updates,
    ) -> MemoryItem:
        memory = self._memory_repo.get(memory_id)
        if memory is None or memory.status == "deleted":
            raise ValueError(f"Memory not found: {memory_id}")
        self._require_write(memory, requester_user_id, requester_group_ids or set())

        title = updates["title"] if "title" in updates else memory.title
        content = updates["content"] if "content" in updates else memory.content
        tags = list(updates["tags"]) if "tags" in updates and updates["tags"] is not None else memory.tags
        owner_user_id = updates["owner_user_id"] if "owner_user_id" in updates else memory.owner_user_id
        owner_group_id = updates["owner_group_id"] if "owner_group_id" in updates else memory.owner_group_id
        owner_agent_id = updates["owner_agent_id"] if "owner_agent_id" in updates else memory.owner_agent_id
        mode = updates["mode"] if "mode" in updates and updates["mode"] is not None else memory.mode
        created_by_agent_id = (
            updates["created_by_agent_id"] if "created_by_agent_id" in updates else memory.created_by_agent_id
        )
        source_discussion_id = (
            updates["source_discussion_id"] if "source_discussion_id" in updates else memory.source_discussion_id
        )
        source_message_ids = (
            list(updates["source_message_ids"])
            if "source_message_ids" in updates and updates["source_message_ids"] is not None
            else memory.source_message_ids
        )
        visibility = updates["visibility"] if "visibility" in updates and updates["visibility"] is not None else memory.visibility
        status = updates["status"] if "status" in updates and updates["status"] is not None else memory.status

        updated = replace(
            memory,
            title=title,
            content=content,
            tags=tags,
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            owner_agent_id=owner_agent_id,
            mode=mode,
            created_by_agent_id=created_by_agent_id,
            source_discussion_id=source_discussion_id,
            source_message_ids=source_message_ids,
            visibility=visibility,
            status=status,
            updated_at=utc_now(),
        )
        self._memory_repo.update(updated)
        return updated

    def search_memories(
        self,
        query: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        owner_user_id: int | None = None,
        owner_group_id: int | None = None,
        owner_agent_id: int | None = None,
        visibility: str | None = None,
        status: str | None = None,
        source_discussion_id: str | None = None,
        include_archived: bool = False,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        candidates = self._memory_repo.search(
            query,
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            owner_agent_id=owner_agent_id,
            visibility=visibility,
            status=status,
            source_discussion_id=source_discussion_id,
            limit=limit,
        )
        return self._filter_visible(
            candidates,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            owner_agent_id=owner_agent_id,
            visibility=visibility,
            status=status,
            source_discussion_id=source_discussion_id,
            include_archived=include_archived,
            include_deleted=include_deleted,
            limit=limit,
        )

    def list_memories(
        self,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        owner_user_id: int | None = None,
        owner_group_id: int | None = None,
        owner_agent_id: int | None = None,
        visibility: str | None = None,
        status: str | None = None,
        source_discussion_id: str | None = None,
        include_archived: bool = False,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        return self._filter_visible(
            self._memory_repo.list_all(),
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            owner_agent_id=owner_agent_id,
            visibility=visibility,
            status=status,
            source_discussion_id=source_discussion_id,
            include_archived=include_archived,
            include_deleted=include_deleted,
            limit=limit,
        )

    def archive_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> MemoryItem:
        return self.update_memory(
            memory_id,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids,
            status="archived",
        )

    def delete_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> MemoryItem:
        return self.update_memory(
            memory_id,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids,
            status="deleted",
        )

    def _filter_visible(
        self,
        memories: list[MemoryItem],
        *,
        requester_user_id: int | None,
        requester_group_ids: set[int],
        owner_user_id: int | None,
        owner_group_id: int | None,
        owner_agent_id: int | None,
        visibility: str | None,
        status: str | None,
        source_discussion_id: str | None,
        include_archived: bool,
        include_deleted: bool,
        limit: int | None,
    ) -> list[MemoryItem]:
        results: list[MemoryItem] = []
        for memory in sorted(memories, key=lambda item: item.updated_at, reverse=True):
            if owner_user_id is not None and memory.owner_user_id != owner_user_id:
                continue
            if owner_group_id is not None and memory.owner_group_id != owner_group_id:
                continue
            if owner_agent_id is not None and memory.owner_agent_id != owner_agent_id:
                continue
            if visibility is not None and memory.visibility != visibility:
                continue
            if status is not None and memory.status != status:
                continue
            if source_discussion_id is not None and memory.source_discussion_id != source_discussion_id:
                continue
            if memory.status == "archived" and not include_archived and status is None:
                continue
            if memory.status == "deleted" and not include_deleted and status is None:
                continue
            if not self._can_view(memory, requester_user_id, requester_group_ids):
                continue
            results.append(memory)
            if limit is not None and len(results) >= limit:
                break
        return results

    def _can_view(self, memory: MemoryItem, requester_user_id: int | None, requester_group_ids: set[int]) -> bool:
        if requester_user_id is None:
            return False
        if memory.owner_user_id is not None and requester_user_id == memory.owner_user_id:
            return True
        if memory.visibility != "user_visible":
            return False
        return can_read(memory, requester_user_id, requester_group_ids)

    def _require_write(
        self,
        memory: MemoryItem,
        requester_user_id: int | None,
        requester_group_ids: set[int],
    ) -> None:
        if requester_user_id is None:
            raise PermissionError("Memory access denied.")
        if memory.owner_user_id is not None and requester_user_id == memory.owner_user_id:
            return
        if not can_write(memory, requester_user_id, requester_group_ids):
            raise PermissionError("Memory access denied.")
