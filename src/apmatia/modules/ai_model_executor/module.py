from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaAiModelExecutorModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_AI_MODEL_EXECUTOR_MODULE = ModuleMetadata(
    module_id="ai_model_executor",
    name="AI Model Executor",
    version="0.1.0",
    description="Local llama.cpp execution control with feasibility checks and process tracking.",
    author="Nick",
    status="development",
    category="integration",
    default_enabled=True,
    tags=("llama.cpp", "execution", "resources", "gpu", "processes"),
    metadata={
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AI_MODEL_EXECUTOR_MODULE)
    register_module_view_provider(APMATIA_AI_MODEL_EXECUTOR_MODULE.module_id, ApmatiaAiModelExecutorModuleViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
