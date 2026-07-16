from __future__ import annotations

from dataclasses import dataclass, field

from apmatia.lib.apmatia_core.models import ApmatiaObject


@dataclass(slots=True)
class GGUFModelRecord(ApmatiaObject):
    name: str = ""
    local_path: str = ""
    file_size_bytes: int = 0
    estimated_ram_bytes: int = 0
    estimated_vram_bytes: int = 0
    size_class: str = ""
    vision_enabled: bool = False
    cost_mode: str = "free"
    input_token_cost_per_1k: float | None = None
    output_token_cost_per_1k: float | None = None
    notes: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TaskSizePreference(ApmatiaObject):
    task_name: str = ""
    preferred_size_classes: tuple[str, ...] = ()
    notes: str = ""
