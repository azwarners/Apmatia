from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agents",
        action_id="agents.agents",
        view_id="agents.agents.view",
        name="Agents",
        description="Create, edit, clone, and remove agents through the Apmatia module API.",
        metadata={
            "object_type": "agent",
            "singular_label": "Agent",
            "plural_label": "Agents",
            "empty_state": "No agents have been created yet.",
            "commands": {verb: f"agents.agents.{verb}" for verb in ("list", "create", "edit", "delete")},
            "schema": {
                "version": 1,
                "resources": {"agents": {"key": "id"}},
            },
            "ui": {"render_mode": "collection", "renderer": "agents"},
        },
    ),
)
