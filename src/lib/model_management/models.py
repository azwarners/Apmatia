from __future__ import annotations

from dataclasses import dataclass, field

from src.lib.apmatia_core.models import ApmatiaObject


@dataclass(slots=True)
class AiModel(ApmatiaObject):
    user_alias: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class LLM(AiModel):
    backend: str = "openai_compatible"
    provider_name: str = ""
    model_url: str = ""
    api_key: str = ""
    max_response_size: int = 8192
    system_prompt: str = ""
