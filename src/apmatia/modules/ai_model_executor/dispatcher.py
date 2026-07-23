from __future__ import annotations

import asyncio
import logging
from typing import Any

from apmatia.modules.ai_model_executor.capacity import CapacityManager
from apmatia.modules.ai_model_executor.executor import ExecutorService
from apmatia.modules.ai_model_executor.models import WorkItem
from apmatia.modules.ai_model_executor.queue import WorkQueue
from apmatia.modules.ai_model_executor.reservation import ReservationManager

logger = logging.getLogger(__name__)


class Dispatcher:
    """
    The Labor Coordinator. Matches eligible work items to available runtime seats.

    Responsibilities:
    - Pull the highest-priority oldest work item from the queue.
    - Acquire a seat lease from the CapacityManager.
    - Hand off to the ExecutorService for actual model inference.
    - Release the seat when done (success or failure).
    - Respect reservation-based admission control so interactive users
      get priority over background work.
    """

    def __init__(
        self,
        queue: WorkQueue,
        capacity_manager: CapacityManager,
        executor_service: ExecutorService,
        reservation_manager: ReservationManager | None = None,
    ):
        self.queue = queue
        self.capacity_manager = capacity_manager
        self.executor = executor_service
        self.reservation_manager = reservation_manager

    async def dispatch_once(self) -> WorkItem | None:
        """
        Attempt to dispatch a single work item from the queue.

        Returns the dispatched WorkItem on success, or None if no work
        was available or could be dispatched.
        """
        work_item = await self.queue.claim_next_eligible()
        if work_item is None:
            return None

        runtime_id = work_item.runtime_id or "llama_cpp"
        lease = None

        try:
            # Check admission control before acquiring a seat
            if not self._admission_allowed(work_item, runtime_id):
                # Put it back in the queue for later
                work_item.status = "queued"
                work_item.claimed_at = None
                await self.queue.repo.save(work_item)
                return None

            # Acquire a seat lease
            lease = await self.capacity_manager.acquire_seat(runtime_id, work_item.id)

            # Execute the work
            work_item.status = "running"
            await self.queue.repo.save(work_item)
            result = await self.executor.execute(work_item)

            # Mark work as completed
            await self.queue.mark_completed(work_item.id, result)
            logger.info("Work item %s completed", work_item.id)

        except Exception as e:
            work_item.status = "failed"
            work_item.error = str(e)
            await self.queue.mark_failed(work_item.id, str(e))
            logger.error("Work item %s failed: %s", work_item.id, e)

        finally:
            # Always release the seat if one was acquired
            if lease is not None:
                await self.capacity_manager.release_seat(lease.id)

        return work_item

    def _admission_allowed(self, work_item: WorkItem, runtime_id: str) -> bool:
        """
        Check whether the work item should be admitted to the executor
        based on reservation-based admission control.

        Background work (priority >= 2) is blocked when an interactive
        reservation holds all available seats.
        """
        if self.reservation_manager is None:
            return True

        if work_item.priority < 2:
            # User or agent work is always admitted
            return True

        state = self.reservation_manager.get_admission_state(runtime_id)
        if state.get("admission_mode") == "interactive_reserved" and state["general_available"] <= 0:
            return False

        return True

    async def run_once(self) -> int:
        """
        Dispatch as many items as there are free seats (up to a small batch).
        Returns the number of items dispatched.
        """
        dispatched = 0
        for _ in range(10):  # max 10 per tick
            result = await self.dispatch_once()
            if result is None:
                break
            dispatched += 1
        return dispatched

    async def run_for(self, duration_seconds: float = 1.0):
        """
        Continuously dispatch work for a limited time window.
        Useful for periodic dispatch loops.
        """
        deadline = asyncio.get_event_loop().time() + duration_seconds
        while asyncio.get_event_loop().time() < deadline:
            dispatched = await self.run_once()
            if dispatched == 0:
                break
            await asyncio.sleep(0.05)
