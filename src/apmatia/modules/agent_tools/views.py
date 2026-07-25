from __future__ import annotations

from apmatia.core.module_view_schema import build_collection_view_schema
from apmatia.core.registry import ViewContribution

from .models import ToolDefinition


AGENT_TOOLS_SCHEMA = build_collection_view_schema(
    ToolDefinition,
    list_fields=("name", "provider_id", "enabled", "confirmation_required", "read_only"),
    create_fields=(
        "name",
        "description",
        "provider_id",
        "enabled",
        "confirmation_required",
        "read_only",
        "input_schema",
        "output_schema",
        "metadata",
    ),
    edit_fields=(
        "name",
        "description",
        "provider_id",
        "enabled",
        "confirmation_required",
        "read_only",
        "input_schema",
        "output_schema",
        "metadata",
    ),
    create={
        "key": "create_agent_tool",
        "title": "Create agent tool",
        "description": "Register a tool definition for assignment to Apmatia agents.",
        "submit_label": "Create agent tool",
        "cancel_label": "Cancel",
    },
    field_overrides={
        "id": {"hidden": True},
        "owner_user_id": {"hidden": True},
        "owner_group_id": {"hidden": True},
        "mode": {"hidden": True},
        "created_at": {"hidden": True},
        "updated_at": {"hidden": True},
        "name": {"required": True, "placeholder": "Tool name"},
        "description": {"field_type": "textarea", "placeholder": "What this tool does"},
        "provider_id": {"required": True, "placeholder": "provider.tool_name"},
        "input_schema": {"field_type": "textarea", "default": {}, "help_text": "JSON object"},
        "output_schema": {"field_type": "textarea", "default": {}, "help_text": "JSON object"},
        "metadata": {"field_type": "textarea", "default": {}, "help_text": "JSON object"},
    },
)


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_tools",
        action_id="agent_tools.agent_tools",
        view_id="agent_tools.agent_tools.view",
        name="Agent Tools",
        description="Create and update tool definitions used by Apmatia agents.",
        metadata={
            "object_type": "agent_tool",
            "singular_label": "Agent Tool",
            "plural_label": "Agent Tools",
            "empty_state": "No agent tools are available yet.",
            "commands": {
                "list": "agent_tools.agent_tools.list",
                "create": "agent_tools.agent_tools.create",
                "edit": "agent_tools.agent_tools.edit",
            },
            "schema": AGENT_TOOLS_SCHEMA,
            "ui": {"render_mode": "collection", "layout": "table-with-actions"},
        },
    ),
)
