from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_mode(mode: int) -> int:
    value = int(mode)
    if value < 0 or value > 0o777:
        raise ValueError("mode must be between 000 and 777")
    return value


@dataclass(slots=True)
class ApmatiaObject:
    id: str | int | None = None
    owner_user_id: int | None = None
    owner_group_id: int | None = None
    mode: int = 0o000
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.mode = _normalize_mode(self.mode)
