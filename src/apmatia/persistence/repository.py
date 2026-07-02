from __future__ import annotations

from collections.abc import Protocol
from typing import Any


class Repository(Protocol):
    def get(self, key: str) -> Any: ...

    def list(self) -> list[Any]: ...
