from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .views import VIEW_DESCRIPTORS

APMATIA_AI_MODEL_EXECUTOR_MODULE = ModuleMetadata(
    module_id="apmatia_ai_model_executor",
    name="Apmatia AI Model Executor",
    version="0.1.0",
    description="Local llama.cpp execution control with feasibility checks and process tracking.",
    metadata={
        "category": "models",
        "tags": ["llama.cpp", "execution", "resources", "processes", "gpu"],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AI_MODEL_EXECUTOR_MODULE)
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
