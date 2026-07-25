from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaPreferencesModuleViewProvider
from .views import VIEW_DESCRIPTORS


APMATIA_PREFERENCES_MODULE = ModuleMetadata(
    module_id="preferences",
    name="Preferences",
    version="0.1.0",
    description="Configure Apmatia runtime, model discovery, agent roots, time zone, appearance, and terminal preferences.",
    author="Nick",
    status="stable",
    category="core",
    default_enabled=True,
    tags=("preferences", "configuration", "appearance", "runtime"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_PREFERENCES_MODULE)
    register_module_view_provider("preferences", ApmatiaPreferencesModuleViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
