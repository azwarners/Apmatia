from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apmatia.core.models import utc_now
from apmatia.modules.ai_model_executor.models import ModelRuntime, SeatLease, RuntimeReservation

class ReservationManager:
    """
    Manages RuntimeReservations to allow interactive users to claim 
    a block of seats, preventing background work from hogging capacity.
    """
    def __init__(self, runtime_repository):
        self.repo = runtime_repository

    async def request_reservation(
        self, 
        runtime_id: str, 
        owner_user_id: int, 
        owner_session_id: str, 
        requested_seats: int = 1, 
        mode: str = "shared"
    ) -> RuntimeReservation:
        reservation = RuntimeReservation(
            id=f"res_{utc_now().timestamp()}",
            runtime_id=runtime_id,
            owner_user_id=owner_user_id,
            owner_session_id=owner_session_id,
            requested_seats=requested_seats,
            mode=mode,
            state="requested"
        )
        self.repo.save_reservation(reservation)
        return reservation

    async def release_reservation(self, reservation_id: str) -> None:
        res = self.repo.get_reservation(reservation_id)
        if res:
            res.state = "released"
            res.released_at = utc_now()
            self.repo.save_reservation(res)

    def get_admission_state(self, runtime_id: str) -> dict[str, Any]:
        runtime = self.repo.get_runtime(runtime_id)
        res = self.repo.get_active_reservation(runtime_id)
        
        total = runtime.max_concurrency
        active_leases = len(self.repo.get_active_leases(runtime_id))
        reserved = res.requested_seats if res else 0
        
        return {
            "total_capacity": total,
            "active_leases": active_leases,
            "reserved_capacity": reserved,
            "general_available": total - active_leases - (reserved if res and res.mode != "shared" else 0),
            "reservation_available": reserved - len([l for l in self.repo.get_active_leases(runtime_id) if l.reservation_id == res.id]) if res else 0,
            "admission_mode": res.mode if res else "none"
        }
