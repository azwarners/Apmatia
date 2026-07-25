from __future__ import annotations

from apmatia.core.registry import ToolContribution

from .tooling import memory_tool_definitions


TOOL_DESCRIPTORS: tuple[ToolContribution, ...] = tuple(
    ToolContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        tool_id=str(definition["name"]),
        name=str(definition["name"]),
        description=str(definition["description"]),
        metadata=dict(definition.get("metadata") or {}),
    )
    for definition in memory_tool_definitions()
)
