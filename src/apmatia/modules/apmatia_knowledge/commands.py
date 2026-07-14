from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="apmatia_knowledge",
        action_id="apmatia_knowledge.agent_config",
        command_id="apmatia_knowledge.agent_config.save",
        path=("apmatia_knowledge", "agent_config", "save"),
        name="Save Agent Config",
        description="Save workspace and knowledge roots for a selected agent.",
        metadata={"object_type": "agent_config", "verb": "save"},
    ),
)
