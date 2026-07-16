from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="agent_config",
        action_id="agent_config.agent_config",
        command_id="agent_config.agent_config.save",
        path=("agent_config", "agent_config", "save"),
        name="Save Agent Config",
        description="Save workspace and knowledge roots for a selected agent.",
        metadata={"object_type": "agent_config", "verb": "save"},
    ),
)
