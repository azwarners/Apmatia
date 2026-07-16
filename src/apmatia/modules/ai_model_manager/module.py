from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaAiModelManagerModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_AI_MODEL_MANAGER_MODULE = ModuleMetadata(
    module_id="ai_model_manager",
    name="Apmatia AI Model Manager",
    version="0.1.0",
    description="Local GGUF model metadata management with size estimates and task routing preferences.",
    metadata={
        "category": "models",
        "tags": ["gguf", "models", "preferences", "scanning", "estimates"],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AI_MODEL_MANAGER_MODULE)
    register_module_view_provider("ai_model_manager", ApmatiaAiModelManagerModuleViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)

