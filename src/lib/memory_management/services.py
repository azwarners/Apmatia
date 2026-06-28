from __future__ import annotations

from typing import Protocol

from .models import MemoryItem


class MemoryService(Protocol):
    def create_memory(self, title: str, content: str, **kwargs) -> MemoryItem:
        raise NotImplementedError

    def get_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        include_deleted: bool = False,
    ) -> MemoryItem | None:
        raise NotImplementedError

    def update_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        **updates,
    ) -> MemoryItem:
        raise NotImplementedError

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
        raise NotImplementedError

    def list_memories(self, **kwargs) -> list[MemoryItem]:
        raise NotImplementedError

    def archive_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> MemoryItem:
        raise NotImplementedError

    def delete_memory(
        self,
        memory_id: int,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> MemoryItem:
        raise NotImplementedError
