from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="agent_config",
        action_id="agent_config.agent_config",
        name="Agent Config",
        description="Configure per-agent workspace and knowledge roots.",
        metadata={"object_type": "agent_config"},
    ),
)
