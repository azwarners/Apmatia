from __future__ import annotations

from typing import Any, Protocol


class Repository(Protocol):
    def get(self, key: str) -> Any: ...

    def list(self) -> list[Any]: ...
