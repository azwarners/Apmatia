from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UIDescriptor:
    ui_id: str
    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
