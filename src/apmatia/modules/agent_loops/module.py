from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry
from apmatia.lib.persistence import logger as persistence_logger

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaAgentLoopsModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_AGENT_LOOPS_MODULE = ModuleMetadata(
    module_id="agent_loops",
    name="Agent Loops",
    version="0.1.0",
    description="A long-running workspace for autonomous contact-driven task loops and run history.",
    metadata={
        "category": "knowledge-work",
        "tags": ["agents", "groups", "loops", "tasks", "workspace", "runs"],
    },
)


def register(registry: Registry) -> None:
    persistence_logger.configure_agent_loop_logging()
    registry.register_module(APMATIA_AGENT_LOOPS_MODULE)
    register_module_view_provider("agent_loops", ApmatiaAgentLoopsModuleViewProvider())
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
