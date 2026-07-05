from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from apmatia.lib.source_inspection.tooling import SOURCE_INSPECTION_PROVIDER_IDS

from .tools import TOOL_DESCRIPTORS

APMATIA_SOURCE_INSPECTION_MODULE = ModuleMetadata(
    module_id="apmatia_source_inspection",
    name="Apmatia Source Inspection",
    version="0.1.0",
    description="Read directories, inspect source files, and trace imports for agent-side architecture review.",
    metadata={
        "category": "developer-tools",
        "tags": ["source", "inspection", "imports", "tree", "read"],
        "provider_ids": sorted(SOURCE_INSPECTION_PROVIDER_IDS.values()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_SOURCE_INSPECTION_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
