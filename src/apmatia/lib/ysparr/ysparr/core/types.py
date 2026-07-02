from dataclasses import dataclass, field
from threading import Event
from typing import Any, Dict

@dataclass(frozen=True)
class PromptRequest:
    prompt_id: str
    prompt_text: str
    model_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    stop_event: Event | None = None

@dataclass(frozen=True)
class ExecutionResult:
    prompt_id: str
    status: str
    output_path: str
