from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .tooling import wiki_tool_definitions
from .tools import TOOL_DESCRIPTORS


APMATIA_KNOWLEDGE_WIKI_MODULE = ModuleMetadata(
    module_id="knowledge_wiki",
    name="Knowledge Wiki",
    version="0.1.0",
    description="Create, organize, search, and maintain hierarchical knowledge wikis.",
    author="Nick",
    status="development",
    category="feature",
    default_enabled=True,
    tags=("knowledge", "wiki", "hierarchy", "agents"),
    metadata={
        "provider_ids": sorted(str(item["provider_id"]) for item in wiki_tool_definitions()),
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_KNOWLEDGE_WIKI_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
