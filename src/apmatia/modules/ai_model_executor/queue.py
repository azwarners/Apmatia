from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.ai_model_executor.models import WorkItem

class WorkQueue:
    """
    Persistent queue for AI work items.
    Consistency: SQLite-backed repository for WorkItems.
    """
    def __init__(self, work_repository):
        self.repo = work_repository

    def enqueue(self, work_item: WorkItem) -> None:
        self.repo.save(work_item)

    def claim_next_eligible(self, runtime_id: str | None = None) -> WorkItem | None:
        """
        Finds the highest priority, oldest queued item compatible with the runtime.
        Atomic transition: queued -> claimed.
        """
        items = self.repo.list_queued(runtime_id=runtime_id)
        if not items:
            return None
        
        # Sort by priority (asc) then created_at (asc)
        item = sorted(items, key=lambda x: (x.priority, x.created_at))[0]
        item.status = \"claimed\"
        item.claimed_at = utc_now()
        self.repo.save(item)
        return item

    def mark_completed(self, work_item_id: str, result: Any) -> None:
        item = self.repo.get(work_item_id)
        if item:
            item.status = \"completed\"
            item.completed_at = utc_now()
            # Result persistence depends on the result model, 
            # but for the first slice, it's often stored in item.metadata or a linked result record.
            self.repo.save(item)
