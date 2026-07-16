from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="ai_host_management",
        action_id="ai_host_management.hosts",
        name="AI Host Inventory",
        description="Manage AI-capable host records.",
        metadata={"object_type": "ai_host"},
    ),
    ActionContribution(
        module_id="ai_host_management",
        action_id="ai_host_management.resources",
        name="AI Host Resources",
        description="Inspect current RAM, VRAM, and GPU utilization for registered AI hosts.",
        metadata={"object_type": "host_resources"},
    ),
)
