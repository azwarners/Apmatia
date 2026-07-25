from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import AgentToolsModuleViewProvider
from .views import VIEW_DESCRIPTORS


APMATIA_AGENT_TOOLS_MODULE = ModuleMetadata(
    module_id="agent_tools",
    name="Agent Tools",
    version="0.1.0",
    description="Define, assign, and safely execute tools used by Apmatia agents.",
    author="Nick",
    status="development",
    category="tool",
    default_enabled=True,
    tags=("agents", "tools", "execution", "assignments"),
    metadata={},
)


def register(registry: Registry) -> None:
    from apmatia.core.tool_management_runtime import get_tool_manager

    registry.register_module(APMATIA_AGENT_TOOLS_MODULE)
    register_module_view_provider("agent_tools", AgentToolsModuleViewProvider(get_tool_manager))
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
