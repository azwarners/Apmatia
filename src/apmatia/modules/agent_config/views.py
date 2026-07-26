from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_config",
        action_id="agent_config.agent_config",
        view_id="agent_config.agent_config.view",
        name="Agent Config",
        description="Select an agent and configure its workspace and knowledge roots.",
        metadata={
            "object_type": "agent_config",
            "ui": {
                "render_mode": "collection",
                "title": "Agent Config",
                "caption": "Choose an agent by name, then update its workspace and knowledge roots. Knowledge roots may be shared across agents; workspace roots usually should not be.",
                "empty_state": "No agents have been created yet.",
                "item_key": "id",
                "columns": [
                    {"key": "name", "label": "Agent"},
                    {"key": "workspace_root", "label": "Workspace Root"},
                    {"key": "knowledge_root", "label": "Knowledge Root"},
                    {"key": "workspace_root_status", "label": "Workspace Status"},
                    {"key": "knowledge_root_status", "label": "Knowledge Status"},
                ],
                "view_actions": [
                    {
                        "key": "save",
                        "label": "Save configuration",
                        "intent": "save",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"command_id": "agent_config.save"},
                    }
                ],
            },
        },
    ),
)
