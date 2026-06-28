from __future__ import annotations

from typing import Protocol

from .models import MemoryItem


class MemoryRepository(Protocol):
    def create(self, memory: MemoryItem) -> int:
        raise NotImplementedError

    def get(self, memory_id: int) -> MemoryItem | None:
        raise NotImplementedError

    def list_all(self) -> list[MemoryItem]:
        raise NotImplementedError

    def search(
        self,
        query: str,
        *,
        owner_user_id: int | None = None,
        owner_group_id: int | None = None,
        owner_agent_id: int | None = None,
        visibility: str | None = None,
        status: str | None = None,
        source_discussion_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        raise NotImplementedError

    def update(self, memory: MemoryItem) -> None:
        raise NotImplementedError
