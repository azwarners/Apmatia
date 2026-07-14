from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaKnowledgeModuleViewProvider
from .tools import TOOL_DESCRIPTORS
from .tooling import KNOWLEDGE_PROVIDER_IDS
from .views import VIEW_DESCRIPTORS

APMATIA_KNOWLEDGE_MODULE = ModuleMetadata(
    module_id="apmatia_knowledge",
    name="Agent Config",
    version="0.1.0",
    description="Configure and inspect agent workspace and knowledge directories.",
    metadata={
        "category": "agent-config",
        "tags": ["agent-config", "knowledge", "workspace", "directories"],
        "provider_ids": sorted(KNOWLEDGE_PROVIDER_IDS.values()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_KNOWLEDGE_MODULE)
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    from apmatia.core.module_view_runtime import register_module_view_provider

    register_module_view_provider("apmatia_knowledge", ApmatiaKnowledgeModuleViewProvider())
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
