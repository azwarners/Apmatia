from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ModuleMetadata:
    module_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
