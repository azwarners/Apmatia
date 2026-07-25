from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import AgentsModuleViewProvider
from .runtime import get_agent_manager
from .views import VIEW_DESCRIPTORS


APMATIA_AGENTS_MODULE = ModuleMetadata(
    module_id="agents",
    name="Agents",
    version="0.1.0",
    description="Create, configure, and manage the agents that power Apmatia.",
    author="Nick",
    status="stable",
    category="agent",
    default_enabled=True,
    tags=("agents", "prompts", "models", "workspaces", "infrastructure"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AGENTS_MODULE)
    register_module_view_provider(
        "agents",
        AgentsModuleViewProvider(manager_factory=get_agent_manager),
    )
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
