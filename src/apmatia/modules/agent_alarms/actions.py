from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        name="Agent Alarms",
        description="Schedule prompts for agents and let Agent Loops run them unattended.",
        metadata={"object_type": "alarm"},
    ),
)
