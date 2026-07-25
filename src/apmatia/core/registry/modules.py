from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ModuleStatus(StrEnum):
    STABLE = "stable"
    DEVELOPMENT = "development"


class ModuleCategory(StrEnum):
    CORE = "core"
    INFRASTRUCTURE = "infrastructure"
    FEATURE = "feature"
    AGENT = "agent"
    TOOL = "tool"
    INTEGRATION = "integration"
    INTERFACE = "interface"
    DEVELOPMENT = "development"
    OTHER = "other"


@dataclass(slots=True)
class ModuleMetadata:
    module_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    status: ModuleStatus = ModuleStatus.DEVELOPMENT
    category: ModuleCategory = ModuleCategory.FEATURE
    default_enabled: bool = True
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, ModuleStatus):
            self.status = ModuleStatus(self.status)
        if not isinstance(self.category, ModuleCategory):
            self.category = ModuleCategory(self.category)
        self.tags = tuple(self.tags)

    @property
    def is_stable(self) -> bool:
        return self.status is ModuleStatus.STABLE

    @property
    def is_development(self) -> bool:
        return self.status is ModuleStatus.DEVELOPMENT

    @property
    def is_visible_by_default(self) -> bool:
        return self.is_stable and self.default_enabled
