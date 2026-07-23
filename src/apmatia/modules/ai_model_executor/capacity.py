from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.ai_model_executor.models import ModelRuntime, SeatLease


class CapacityManager:
    """
    Manages the logical concurrency permits (seats) for model runtimes.
    Consistency: asyncio.Semaphore (in-memory) <-> SeatLease (persisted).
    """
    def __init__(self, runtime_repository):
        self.repo = runtime_repository
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        # Track each runtime's actual max_concurrency so release() can find the right semaphore
        self._max_concurrency: dict[str, int] = {}
        # Lock to protect semaphore creation during concurrent claim/release
        self._lock = asyncio.Lock()

    def _init_semaphore(self, runtime_id: str, max_concurrency: int) -> asyncio.Semaphore:
        if runtime_id not in self._semaphores:
            self._semaphores[runtime_id] = asyncio.Semaphore(max_concurrency)
            self._max_concurrency[runtime_id] = max_concurrency
        return self._semaphores[runtime_id]

    async def acquire_seat(self, runtime_id: str, owner_id: str) -> SeatLease:
        runtime = self.repo.get_runtime(runtime_id)
        if not runtime:
            raise ValueError(f"Runtime '{runtime_id}' not found")

        async with self._lock:
            sem = self._init_semaphore(runtime_id, runtime.max_concurrency)

        await sem.acquire()

        lease = SeatLease(
            id=f"lease_{utc_now().isoformat()}",
            runtime_id=runtime_id,
            owner_id=owner_id,
            status="active"
        )
        self.repo.save_lease(lease)
        return lease

    async def release_seat(self, lease_id: str):
        lease = self.repo.get_lease(lease_id)
        if not lease or lease.status != "active":
            return

        lease.status = "released"
        lease.released_at = utc_now()
        self.repo.save_lease(lease)

        async with self._lock:
            sem = self._semaphores.get(lease.runtime_id)
            if sem is not None:
                sem.release()
