from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaModuleManagerViewProvider
from .views import VIEW_DESCRIPTORS


APMATIA_MODULE_MANAGER_MODULE = ModuleMetadata(
    module_id="module_manager",
    name="Module Manager",
    version="0.1.0",
    description="Configure active modules and the visibility and order of module views.",
    author="Nick",
    status="stable",
    category="core",
    default_enabled=True,
    tags=("modules", "configuration", "navigation"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_MODULE_MANAGER_MODULE)
    register_module_view_provider("module_manager", ApmatiaModuleManagerViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
