from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="agent_tools",
        action_id="agent_tools.agent_tools",
        name="Agent Tools",
        description="Browse and manage tool definitions available to Apmatia agents.",
        metadata={"object_type": "agent_tool"},
    ),
)
