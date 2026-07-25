from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaMemoryManagerModuleViewProvider
from .tooling import memory_tool_definitions
from .tools import TOOL_DESCRIPTORS
from .views import VIEW_DESCRIPTORS


APMATIA_MEMORY_MANAGER_MODULE = ModuleMetadata(
    module_id="memory_manager",
    name="Memory Manager",
    version="0.1.0",
    description="Persist, browse, edit, archive, and delete agent memories.",
    author="Nick",
    status="development",
    category="agent",
    default_enabled=True,
    tags=("memory", "agents", "persistence", "knowledge"),
    metadata={"provider_ids": sorted(str(item["provider_id"]) for item in memory_tool_definitions())},
)


def register(registry: Registry) -> None:
    from apmatia.core.agent_management_runtime import get_agent_manager
    from apmatia.core.memory_management_runtime import get_memory_manager

    registry.register_module(APMATIA_MEMORY_MANAGER_MODULE)
    register_module_view_provider(
        "memory_manager",
        ApmatiaMemoryManagerModuleViewProvider(
            manager_factory=get_memory_manager,
            agent_manager_factory=get_agent_manager,
        ),
    )
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
