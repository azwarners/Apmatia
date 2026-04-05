from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass(frozen=True)
class PromptRequest:
    prompt_id: str
    prompt_text: str
    model_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecutionResult:
    prompt_id: str
    status: str
    output_path: str
