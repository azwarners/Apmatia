from __future__ import annotations

from typing import Any, Protocol


class Store(Protocol):
    def read(self, path: str) -> Any: ...

    def write(self, path: str, value: Any) -> None: ...
