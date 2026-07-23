from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from apmatia.lib.dev_tools.tooling import DEV_TOOLS_PROVIDER_IDS

from .tools import TOOL_DESCRIPTORS

APMATIA_DEV_TOOLS_MODULE = ModuleMetadata(
    module_id="dev_tools",
    name="Dev Tools",
    version="0.1.0",
    description="Read directories, inspect source files, and trace imports for agent-side development review.",
    metadata={
        "category": "developer-tools",
        "tags": ["source", "inspection", "imports", "tree", "read"],
        "provider_ids": sorted(DEV_TOOLS_PROVIDER_IDS.values()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_DEV_TOOLS_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
