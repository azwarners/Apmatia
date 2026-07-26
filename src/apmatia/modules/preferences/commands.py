from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="preferences",
        command_id="preferences.save",
        path=("preferences", "save"),
        name="Save Preferences",
        description="Save Apmatia's local preferences.",
        metadata={"object_type": "preferences", "verb": "save"},
    ),
)
