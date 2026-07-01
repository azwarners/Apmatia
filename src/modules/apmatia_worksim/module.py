from __future__ import annotations

from src.core.module_view_runtime import register_module_view_provider
from src.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaWorksimModuleViewProvider
from .tools import TOOL_DESCRIPTORS
from .views import VIEW_DESCRIPTORS

APMATIA_WORKSIM_MODULE = ModuleMetadata(
    module_id="apmatia_worksim",
    name="Apmatia Worksim",
    version="0.1.0",
    description="A workplace simulation module centered on a persistent org chart wiki.",
    metadata={
        "category": "workspace",
        "tags": ["wiki", "org-chart", "agents", "teams", "simulation"],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_WORKSIM_MODULE)
    register_module_view_provider("apmatia_worksim", ApmatiaWorksimModuleViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
