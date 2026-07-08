from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .tools import TOOL_DESCRIPTORS
from .tooling import KNOWLEDGE_PROVIDER_IDS

APMATIA_KNOWLEDGE_MODULE = ModuleMetadata(
    module_id="apmatia_knowledge",
    name="Apmatia Knowledge",
    version="0.1.0",
    description="Agent tools for browsing and reading files in ~/.apmatia/workspace/knowledge.",
    metadata={
        "category": "knowledge",
        "tags": ["knowledge", "tree", "read", "workspace"],
        "provider_ids": sorted(KNOWLEDGE_PROVIDER_IDS.values()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_KNOWLEDGE_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
