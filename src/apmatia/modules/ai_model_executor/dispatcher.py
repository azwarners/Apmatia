from __future__ import annotations

import asyncio
from typing import Any

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.ai_model_executor.models import WorkItem, SeatLease
from apmatia.modules.ai_model_executor.capacity import CapacityManager
from apmatia.modules.ai_model_executor.queue import WorkQueue

class Dispatcher:
    """
    The Labor Coordinator. Matches eligible work items to available runtime seats.
    """
    def __init__(self, queue: WorkQueue, capacity_manager: CapacityManager, executor_service):
        self.queue = queue
        self.capacity_manager = capacity_manager
        self.executor = executor_service

    async def dispatch_once(self) -> WorkItem | None:
        """
        Attempts to dispatch a single work item from the queue.
        """
        # 1. Find a claimed item from the queue
        work_item = self.queue.claim_next_eligible()
        if not work_item:
            return None

        runtime_id = work_item.runtime_id or \"default\"
        
        try:
            # 2. Acquire a seat lease
            lease = await self.capacity_manager.acquire_seat(runtime_id, work_item.id)
            
            # 3. Execute the work
            work_item.status = \"running\"
            result = await self.executor.execute(work_item)
            
            # 4. Mark work as completed
            self.queue.mark_completed(work_item.id, result)
            
        except Exception as e:
            work_item.status = \"failed\"
            work_item.error = str(e)
            self.queue.repo.save(work_item)
        finally:
            # 5. Always release the seat if one was acquired
            if \"lease\" in locals():
                await self.capacity_manager.release_seat(lease.id)
        
        return work_item

    async def run_until_idle(self, timeout: float = 1.0):
        """
        Continuously dispatch work until the queue is empty or a timeout occurs.
        """
        while True:
            start_time = asyncio.get_event_loop().time()
            await self.dispatch_once()
            if asyncio.get_event_loop().time() - start_time > timeout:
                break
