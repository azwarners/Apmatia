from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import AgentAlarmsModuleViewProvider
from .service import get_agent_alarm_service
from .views import VIEW_DESCRIPTORS

AGENT_ALARMS_MODULE = ModuleMetadata(
    module_id="agent_alarms",
    name="Agent Alarms",
    version="0.1.0",
    description="An experimental alarm scheduler that dispatches due prompts to Agent Loops.",
    metadata={
        "category": "automation",
        "tags": ["alarms", "scheduler", "agent-loops", "automation"],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(AGENT_ALARMS_MODULE)
    register_module_view_provider("agent_alarms", AgentAlarmsModuleViewProvider(service_factory=get_agent_alarm_service))
    get_agent_alarm_service()
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
