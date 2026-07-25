from __future__ import annotations

from apmatia.core.module_view_schema import build_collection_view_schema
from apmatia.core.registry import ViewContribution

from .models import MemoryItem


MEMORY_SCHEMA = build_collection_view_schema(
    MemoryItem,
    list_fields=("title", "owner_agent_id", "visibility", "status", "tags"),
    create_fields=("title", "content", "tags", "owner_agent_id", "visibility", "source_discussion_id", "source_message_ids"),
    edit_fields=("title", "content", "tags", "owner_agent_id", "visibility", "status", "source_discussion_id", "source_message_ids"),
    create={
        "key": "create_memory",
        "title": "Create memory",
        "description": "Persist a memory for an agent or for your user account.",
        "submit_label": "Create memory",
        "cancel_label": "Cancel",
    },
    field_overrides={
        "id": {"hidden": True},
        "owner_user_id": {"hidden": True},
        "owner_group_id": {"hidden": True},
        "mode": {"hidden": True},
        "created_at": {"hidden": True},
        "updated_at": {"hidden": True},
        "created_by_agent_id": {"hidden": True},
        "title": {"required": True, "placeholder": "Short memory title"},
        "content": {"required": True, "field_type": "textarea", "placeholder": "Memory content"},
        "tags": {"field_type": "text", "placeholder": "comma, separated, tags"},
        "owner_agent_id": {
            "label": "Agent ID",
            "field_type": "text",
            "help_text": "Leave blank for a user-owned memory.",
        },
        "visibility": {"field_type": "select", "options": ["draft", "user_visible", "private"]},
        "status": {"field_type": "select", "options": ["active", "archived", "deleted"]},
        "source_discussion_id": {"label": "Source Discussion ID"},
        "source_message_ids": {"field_type": "text", "placeholder": "comma, separated, message IDs"},
    },
)


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        view_id="memory_manager.memory.view",
        name="Memories",
        description="Browse and manage memories visible to your user and groups.",
        metadata={
            "object_type": "memory",
            "singular_label": "Memory",
            "plural_label": "Memories",
            "empty_state": "No memories found.",
            "commands": {
                "list": "memory_manager.memory.list",
                "create": "memory_manager.memory.create",
                "edit": "memory_manager.memory.edit",
                "delete": "memory_manager.memory.delete",
            },
            "schema": MEMORY_SCHEMA,
            "ui": {"render_mode": "collection", "layout": "table-with-actions"},
        },
    ),
)
