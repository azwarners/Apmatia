from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaIpeModuleViewProvider
from .tools import TOOL_DESCRIPTORS
from .views import VIEW_DESCRIPTORS

APMATIA_IPE_MODULE = ModuleMetadata(
    module_id="ipe",
    name="Apmatia Integrated Productivity Environment",
    version="0.1.0",
    description="An integrated workspace for ideas, tasks, projects, habits, and calendar planning.",
    metadata={
        "category": "productivity",
        "tags": ["ideas", "tasks", "projects", "habits", "calendar", "assistant"],
    },
)


def register(registry: Registry) -> None:
    from apmatia.core.ipe_runtime import get_ipe_service

    registry.register_module(APMATIA_IPE_MODULE)
    register_module_view_provider("ipe", ApmatiaIpeModuleViewProvider(service_factory=get_ipe_service))
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
