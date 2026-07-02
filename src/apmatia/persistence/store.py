from __future__ import annotations

from collections.abc import Protocol
from typing import Any


class Store(Protocol):
    def read(self, path: str) -> Any: ...

    def write(self, path: str, value: Any) -> None: ...
