from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="preferences",
        action_id="preferences.preferences",
        name="Preferences",
        description="Configure Apmatia preferences.",
        metadata={"object_type": "preferences"},
    ),
)
