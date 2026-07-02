from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PersistenceDescriptor:
    persistence_id: str
    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RepositoryDescriptor(PersistenceDescriptor):
    repository_kind: str = "repository"


@dataclass(slots=True)
class StoreDescriptor(PersistenceDescriptor):
    store_kind: str = "store"
