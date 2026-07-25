from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        name="Memories",
        description="Browse and manage persisted agent memories.",
        metadata={"object_type": "memory"},
    ),
)
