from __future__ import annotations

from .descriptors import PersistenceDescriptor


class PersistenceRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, PersistenceDescriptor] = {}

    def register(self, descriptor: PersistenceDescriptor) -> None:
        self._descriptors[descriptor.persistence_id] = descriptor

    def get(self, persistence_id: str) -> PersistenceDescriptor | None:
        return self._descriptors.get(persistence_id)

    def list(self) -> list[PersistenceDescriptor]:
        return [self._descriptors[persistence_id] for persistence_id in sorted(self._descriptors)]
