from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="module_manager",
        action_id="module_manager.module_manager",
        name="Module Manager",
        description="Configure module activation, visibility, and navigation order.",
        metadata={"object_type": "module_catalog"},
    ),
)
