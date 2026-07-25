from __future__ import annotations

from dataclasses import dataclass, field

from apmatia.core.models import ApmatiaObject


@dataclass(slots=True)
class AiModel(ApmatiaObject):
    """Base class for model-related objects."""
    user_alias: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GGUFModelRecord(ApmatiaObject):
    name: str = ""
    local_path: str = ""
    file_size_bytes: int = 0
    estimated_ram_bytes: int = 0
    estimated_vram_bytes: int = 0
    size_class: str = ""
    seats: int = 1
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


@dataclass(slots=True)
class LLMConfig(ApmatiaObject):
    """Remote LLM endpoint configuration (OpenAI-compatible API)."""
    user_alias: str = ""
    backend: str = "openai_compatible"
    provider_name: str = ""
    model_url: str = ""
    api_key: str = ""
    max_response_size: int = 8192
    seats: int = 1
    system_prompt: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

