from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="memory_manager",
        command_id=f"memory_manager.{verb}",
        path=("memory_manager", verb),
        name=f"Memory {verb.title()}",
        description=f"{verb.title()} a persisted memory.",
        metadata={
            "object_type": "memory",
            "verb": verb,
            "collection_view_id": "memory_manager.memory.view",
        },
    )
    for verb in ("list", "create", "edit", "delete")
)
