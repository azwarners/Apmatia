from dataclasses import dataclass, field
from typing import Any

from apmatia.lib.apmatia_core.models import ApmatiaObject


@dataclass(slots=True)
class Agent(ApmatiaObject):
    name: str = ""
    prompt_id: int | None = None
    system_prompt_id: int = 0
    memory_id: int = 0
    rag_root_ids: list[int] = field(default_factory=list)
    tool_ids: list[int] = field(default_factory=list)
    default_model_id: int | None = None
    active_model_id: int | None = None
    workspace_root: str = ""
    knowledge_root: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
