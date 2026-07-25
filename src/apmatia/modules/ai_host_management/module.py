from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaAIHostManagementModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_AI_HOST_MANAGEMENT_MODULE = ModuleMetadata(
    module_id="ai_host_management",
    name="AI Host Management",
    version="0.1.0",
    description="Track AI-capable hosts and inspect current resource utilization across registered hosts for future model placement.",
    author="Nick",
    status="development",
    category="infrastructure",
    default_enabled=True,
    tags=("hosts", "resources", "ssh", "local", "inventory"),
    metadata={
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AI_HOST_MANAGEMENT_MODULE)
    register_module_view_provider(
        "ai_host_management",
        ApmatiaAIHostManagementModuleViewProvider(),
    )
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in _view_descriptors():
        registry.register_view(view)


def _view_descriptors() -> tuple:
    if isinstance(VIEW_DESCRIPTORS, tuple):
        return VIEW_DESCRIPTORS
    return (VIEW_DESCRIPTORS,)
