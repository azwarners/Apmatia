from __future__ import annotations

from datetime import datetime

from apmatia.core.module_view_schema import build_collection_view_schema
from apmatia.core.registry import ViewContribution

from .models import AgentAlarm


ALARM_COLLECTION_VIEW_SCHEMA = build_collection_view_schema(
    AgentAlarm,
    list_fields=("name", "agent_id", "model_id", "scheduled_start_time", "status", "enabled", "last_result", "last_error"),
    create_fields=("name", "agent_id", "prompt", "model_id", "scheduled_start_time", "enabled"),
    edit_fields=("name", "agent_id", "prompt", "model_id", "scheduled_start_time", "enabled", "status"),
    field_overrides={
        "id": {"hidden": True},
        "owner_user_id": {"hidden": True},
        "owner_group_id": {"hidden": True},
        "mode": {"hidden": True},
        "created_at": {"hidden": True},
        "updated_at": {"hidden": True},
        "name": {"placeholder": "Nightly summary"},
        "agent_id": {"label": "Agent", "help_text": "The agent that will execute the alarm."},
        "prompt": {
            "field_type": "textarea",
            "help_text": "The prompt the agent should execute when the alarm fires.",
            "placeholder": "Review the last 24 hours and prepare a concise report.",
        },
        "model_id": {"label": "Model", "help_text": "Explicit model override to use for this alarm."},
        "scheduled_start_time": {
            "label": "Scheduled start time",
            "placeholder": datetime.now().astimezone().isoformat(timespec="minutes"),
            "help_text": "Timezone-aware ISO 8601 timestamp.",
        },
        "enabled": {"label": "Enabled"},
        "status": {
            "field_type": "select",
            "options": ["scheduled", "running", "completed", "failed", "disabled"],
            "default": "scheduled",
        },
        "started_at": {"hidden": True},
        "completed_at": {"hidden": True},
        "launched_loop_run_id": {"hidden": True},
        "last_result": {"hidden": True},
        "last_error": {"hidden": True},
    },
    create={
        "title": "Create alarm",
        "description": "Schedule an agent prompt for a future start time using date and time pickers.",
        "submit_label": "Create alarm",
        "fields": [
            {"key": "name", "label": "Alarm name", "placeholder": "Nightly summary"},
            {
                "key": "agent_id",
                "label": "Agent",
                "field_type": "select",
                "help_text": "Choose the agent that will execute this alarm.",
                "options": (),
            },
            {
                "key": "prompt",
                "label": "Prompt",
                "field_type": "textarea",
                "help_text": "The prompt the agent should execute when the alarm fires.",
                "placeholder": "Review the last 24 hours and prepare a concise report.",
            },
            {
                "key": "model_id",
                "label": "Model",
                "field_type": "select",
                "help_text": "Choose the model alias to use for this alarm.",
                "options": (),
            },
            {
                "key": "scheduled_start_date",
                "label": "Scheduled date",
                "field_type": "date",
                "help_text": "Pick the day the alarm should start.",
            },
            {
                "key": "scheduled_start_time",
                "label": "Scheduled time",
                "field_type": "time",
                "help_text": "Pick the time of day the alarm should start.",
            },
            {
                "key": "enabled",
                "label": "Enabled",
                "field_type": "checkbox",
                "default": True,
                "help_text": "Leave enabled to schedule the alarm immediately.",
            },
        ],
    },
)

_ALARM_EDIT_FORM_FIELDS = [
    {"key": "name", "label": "Alarm name", "placeholder": "Nightly summary"},
    {
        "key": "agent_id",
        "label": "Agent",
        "field_type": "select",
        "help_text": "Choose the agent that will execute this alarm.",
        "options": (),
    },
    {
        "key": "prompt",
        "label": "Prompt",
        "field_type": "textarea",
        "help_text": "The prompt the agent should execute when the alarm fires.",
        "placeholder": "Review the last 24 hours and prepare a concise report.",
    },
    {
        "key": "model_id",
        "label": "Model",
        "field_type": "select",
        "help_text": "Choose the model alias to use for this alarm.",
        "options": (),
    },
    {
        "key": "scheduled_start_date",
        "label": "Scheduled date",
        "field_type": "date",
        "help_text": "Pick the day the alarm should start.",
    },
    {
        "key": "scheduled_start_time",
        "label": "Scheduled time",
        "field_type": "time",
        "help_text": "Pick the time of day the alarm should start.",
    },
    {
        "key": "enabled",
        "label": "Enabled",
        "field_type": "checkbox",
        "default": True,
        "help_text": "Disable this alarm to pause it without deleting it.",
    },
]


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        view_id="agent_alarms.alarms.view",
        name="Agent Alarms",
        description="Schedule autonomous alarm-style agent runs.",
        metadata={
            "object_type": "alarm",
            "singular_label": "Alarm",
            "plural_label": "Alarms",
            "empty_state": "No alarms have been created yet.",
            "schema": ALARM_COLLECTION_VIEW_SCHEMA,
            "ui": {
                "render_mode": "collection",
                "title": "Agent Alarms",
                "caption": "Create alarms that wake an agent up at a specific time and hand the work to Agent Loops.",
                "create_form": {
                    "key": "create_alarm",
                    "title": "Create alarm",
                    "description": "Schedule an alarm with friendly dropdowns and separate date/time pickers.",
                    "submit_label": "Create alarm",
                    "fields": [
                        {"key": "name", "label": "Alarm name", "placeholder": "Nightly summary"},
                        {
                            "key": "agent_id",
                            "label": "Agent",
                            "field_type": "select",
                            "help_text": "Choose the agent that will execute this alarm.",
                            "options": (),
                        },
                        {
                            "key": "prompt",
                            "label": "Prompt",
                            "field_type": "textarea",
                            "help_text": "The prompt the agent should execute when the alarm fires.",
                            "placeholder": "Review the last 24 hours and prepare a concise report.",
                        },
                        {
                            "key": "model_id",
                            "label": "Model",
                            "field_type": "select",
                            "help_text": "Choose the model alias to use for this alarm.",
                            "options": (),
                        },
                        {
                            "key": "scheduled_start_date",
                            "label": "Scheduled date",
                            "field_type": "date",
                            "help_text": "Pick the day the alarm should start.",
                        },
                        {
                            "key": "scheduled_start_time",
                            "label": "Scheduled time",
                            "field_type": "time",
                            "help_text": "Pick the time of day the alarm should start.",
                        },
                        {
                            "key": "enabled",
                            "label": "Enabled",
                            "field_type": "checkbox",
                            "default": True,
                            "help_text": "Leave enabled to schedule the alarm immediately.",
                        },
                    ],
                },
                "edit_form": {
                    "key": "edit_alarm",
                    "title": "Edit alarm",
                    "description": "Adjust the alarm details, date, and time before re-arming it.",
                    "submit_label": "Save changes",
                    "fields": list(_ALARM_EDIT_FORM_FIELDS),
                },
                "columns": [
                    {"key": "name", "label": "Alarm"},
                    {"key": "agent_name", "label": "Agent"},
                    {"key": "model_name", "label": "Model"},
                    {"key": "scheduled_start_time_display", "label": "Scheduled"},
                    {"key": "status_label", "label": "Status"},
                    {"key": "enabled_label", "label": "Enabled"},
                    {"key": "result_summary", "label": "Result"},
                    {"key": "error_summary", "label": "Error"},
                ],
                "view_actions": [
                    {
                        "key": "create",
                        "label": "Create alarm",
                        "intent": "create",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"command_id": "agent_alarms.alarms.create"},
                    }
                ],
                "item_actions": [
                    {
                        "key": "edit",
                        "label": "Edit",
                        "intent": "edit",
                        "scope": "item",
                        "style": "secondary",
                        "payload": {"command_id": "agent_alarms.alarms.edit"},
                    },
                    {
                        "key": "delete",
                        "label": "Delete",
                        "intent": "delete",
                        "scope": "item",
                        "style": "secondary",
                        "confirmation": True,
                        "payload": {"command_id": "agent_alarms.alarms.delete"},
                    },
                ],
                "commands": {
                    "create": "agent_alarms.alarms.create",
                    "delete": "agent_alarms.alarms.delete",
                    "edit": "agent_alarms.alarms.edit",
                    "list": "agent_alarms.alarms.list",
                },
            },
        },
    ),
)
