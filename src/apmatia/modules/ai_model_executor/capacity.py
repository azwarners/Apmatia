from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.ai_model_executor.models import ModelRuntime, SeatLease

class CapacityManager:
    \"\"\"
    Manages the logical concurrency permits (seats) for model runtimes.
    Consistency: asyncio.Semaphore (in-memory) <-> SeatLease (persisted).
    \"\"\"
    def __init__(self, runtime_repository):
        self.repo = runtime_repository
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_semaphore(self, runtime_id: str, max_concurrency: int) -> asyncio.Semaphore:
        if runtime_id not in self._semaphores:
            self._semaphores[runtime_id] = asyncio.Semaphore(max_concurrency)
        return self._semaphores[runtime_id]

    async def acquire_seat(self, runtime_id: str, owner_id: str) -> SeatLease:
        runtime = self.repo.get_runtime(runtime_id)
        sem = self._get_semaphore(runtime_id, runtime.max_concurrency)
        
        await sem.acquire()
        
        lease = SeatLease(
            id=f\"lease_{utc_now().timestamp()}\", # Simplified ID for first slice
            runtime_id=runtime_id,
            owner_id=owner_id,
            status=\"active\"
        )
        self.repo.save_lease(lease)
        return lease

    async def release_seat(self, lease_id: str):
        lease = self.repo.get_lease(lease_id)
        if lease and lease.status == \"active\":
            lease.status = \"released\"
            lease.released_at = utc_now()
            self.repo.save_lease(lease)
            
            sem = self._get_semaphore(lease.runtime_id, 1) # max_concurrency handled by sem
            sem.release()
