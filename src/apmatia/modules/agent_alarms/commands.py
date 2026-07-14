from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        command_id="agent_alarms.alarms.list",
        name="List alarms",
        description="List all scheduled alarms.",
        metadata={"object_type": "alarm", "verb": "list"},
    ),
    CommandContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        command_id="agent_alarms.alarms.create",
        name="Create alarm",
        description="Create a new alarm.",
        metadata={"object_type": "alarm", "verb": "create"},
    ),
    CommandContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        command_id="agent_alarms.alarms.edit",
        name="Edit alarm",
        description="Edit an existing alarm and optionally re-arm it.",
        metadata={"object_type": "alarm", "verb": "edit"},
    ),
    CommandContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        command_id="agent_alarms.alarms.delete",
        name="Delete alarm",
        description="Delete an alarm.",
        metadata={"object_type": "alarm", "verb": "delete"},
    ),
)
