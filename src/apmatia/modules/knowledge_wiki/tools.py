from __future__ import annotations

from apmatia.core.registry import ToolContribution

from .tooling import wiki_tool_definitions


TOOL_DESCRIPTORS: tuple[ToolContribution, ...] = tuple(
    ToolContribution(
        module_id="knowledge_wiki",
        action_id="knowledge_wiki.wiki",
        tool_id=str(definition["name"]),
        name=str(definition["name"]),
        description=str(definition["description"]),
        metadata=dict(definition.get("metadata") or {}),
    )
    for definition in wiki_tool_definitions()
)
