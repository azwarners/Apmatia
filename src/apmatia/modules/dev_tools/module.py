from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .tooling import DEV_TOOLS_PROVIDER_IDS

from .tools import TOOL_DESCRIPTORS

APMATIA_DEV_TOOLS_MODULE = ModuleMetadata(
    module_id="dev_tools",
    name="Dev Tools",
    version="0.1.0",
    description="Developer tools for tree inspection, source reading, and dependency tracing.",
    author="Nick",
    status="development",
    category="development",
    default_enabled=True,
    tags=("tree", "source", "imports", "inspection"),
    metadata={
        "provider_ids": sorted(DEV_TOOLS_PROVIDER_IDS.values()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_DEV_TOOLS_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
