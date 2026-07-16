from __future__ import annotations

from apmatia.core.registry import ViewContribution

from .collections import PARTICIPANT_VIEW_SPEC


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="contacts_and_discussions",
        action_id=PARTICIPANT_VIEW_SPEC.action_id,
        view_id=PARTICIPANT_VIEW_SPEC.view_id,
        name="Chat Targets View",
        description="Choose an agent or group, keep the active chat roster in one place, and resume discussions from the same screen.",
        metadata={
            "ui": {
                "render_mode": "collection",
                "layout": "table-with-actions",
                "title": "Chat Targets",
                "caption": "Choose an agent or group, keep the active chat roster in one place, and resume discussions from the same screen.",
                "empty_state": "No chat targets have been recorded yet.",
                "item_key": "id",
                "columns": list(PARTICIPANT_VIEW_SPEC.columns),
                "nav_pane": {
                    "title": "Contacts",
                    "top_exit_label": "Back to Apmatia",
                    "bottom_exit_label": "Back to Apmatia",
                    "empty_state": "No contacts are available yet.",
                    "item_label_key": "title",
                    "item_subtitle_key": "chat_preview",
                    "item_detail_key": "last_activity_at",
                    "item_value_key": "id",
                },
                "create_form": (
                    {
                        "key": "participant-create",
                        "title": "Add a chat target",
                        "description": "Pick an agent or group first, then tune how Apmatia should chat with it.",
                        "submit_label": "Save target",
                        "fields": [
                            {
                                "key": "chat_target",
                                "label": "Chat target",
                                "field_type": "select",
                                "help_text": "This is the agent or group you want Apmatia to follow.",
                                "options": (),
                            },
                            {
                                "key": "selected_model_id",
                                "label": "Model alias",
                                "field_type": "select",
                                "help_text": "Optional runtime model alias to associate with this target.",
                                "options": (),
                            },
                            {
                                "key": "role",
                                "label": "Role",
                                "field_type": "select",
                                "options": ("agent", "coordinator", "reviewer", "observer"),
                                "help_text": "How this target should participate when it joins a conversation.",
                            },
                            {
                                "key": "turn_policy",
                                "label": "Turn policy",
                                "field_type": "select",
                                "options": ("manual", "auto", "round_robin", "coordinator_only"),
                                "help_text": "How turns should be scheduled for group-style chat.",
                            },
                            {
                                "key": "temperature_override",
                                "label": "Temperature override",
                                "field_type": "number",
                                "min_value": 0.0,
                                "max_value": 2.0,
                                "step": 0.1,
                            },
                            {
                                "key": "tool_restrictions",
                                "label": "Tool restrictions",
                                "field_type": "text",
                                "placeholder": "wiki.read, memory.write",
                            },
                        ],
                    }
                ),
                "commands": {
                    "create": PARTICIPANT_VIEW_SPEC.create_command_id,
                    "edit": PARTICIPANT_VIEW_SPEC.edit_command_id,
                    "delete": PARTICIPANT_VIEW_SPEC.delete_command_id,
                },
            },
            "schema": dict(PARTICIPANT_VIEW_SPEC.schema),
            "object_type": PARTICIPANT_VIEW_SPEC.object_type,
            "singular_label": PARTICIPANT_VIEW_SPEC.singular_label,
            "plural_label": PARTICIPANT_VIEW_SPEC.plural_label,
            "empty_state": "No chat targets have been recorded yet.",
        },
    ),
)
