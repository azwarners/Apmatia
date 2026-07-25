from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="preferences",
        action_id="preferences.preferences",
        command_id="preferences.preferences.save",
        path=("preferences", "preferences", "save"),
        name="Save Preferences",
        description="Save Apmatia's local preferences.",
        metadata={"object_type": "preferences", "verb": "save"},
    ),
)
