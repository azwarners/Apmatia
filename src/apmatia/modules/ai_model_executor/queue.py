from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from apmatia.core.models import utc_now
from apmatia.modules.ai_model_executor.models import WorkItem


class WorkQueue:
    """
    Persistent queue for AI work items.
    Consistency: SQLite-backed repository for WorkItems.
    Thread-safe: uses an asyncio.Lock for atomic claim operations.
    """
    def __init__(self, work_repository):
        self.repo = work_repository
        self._claim_lock = asyncio.Lock()

    def enqueue(self, work_item: WorkItem) -> None:
        self.repo.save(work_item)

    async def claim_next_eligible(self, runtime_id: str | None = None) -> WorkItem | None:
        """
        Finds the highest priority, oldest queued item compatible with the runtime.
        Atomic transition: queued -> claimed (protected by asyncio.Lock).
        """
        async with self._claim_lock:
            items = self.repo.list_queued(runtime_id=runtime_id)
            if not items:
                return None

            # Sort by priority (asc = higher priority first), then by created_at (oldest first)
            eligible = sorted(items, key=lambda x: (x.priority, x.created_at))
            item = eligible[0]

            # Double-check status in case another coroutine snuck in
            if item.status != "queued":
                return None

            item.status = "claimed"
            item.claimed_at = utc_now()
            self.repo.save(item)
            return item

    async def mark_completed(self, work_item_id: str, result: Any) -> None:
        async with self._claim_lock:
            item = self.repo.get(work_item_id)
            if item and item.status == "claimed":
                item.status = "completed"
                item.completed_at = utc_now()
                self.repo.save(item)

    async def mark_failed(self, work_item_id: str, error: str) -> None:
        async with self._claim_lock:
            item = self.repo.get(work_item_id)
            if item and item.status in ("claimed", "running"):
                item.status = "failed"
                item.error = error
                item.completed_at = utc_now()
                self.repo.save(item)
