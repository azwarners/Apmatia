from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="agents",
        action_id="agents.agents",
        name="Agents",
        description="Create, configure, clone, and remove Apmatia agents.",
        metadata={"object_type": "agent"},
    ),
)
