from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ViewContribution:
    module_id: str
    action_id: str
    view_id: str
    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
