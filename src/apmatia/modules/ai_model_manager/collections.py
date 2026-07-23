from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.core.module_view_schema import build_collection_view_schema

from .models import GGUFModelRecord, LLMConfig, TaskSizePreference


@dataclass(frozen=True, slots=True)
class AiModelCollectionViewSpec:
    action_id: str
    view_id: str
    object_type: str
    singular_label: str
    plural_label: str
    description: str
    schema: dict[str, Any]
    list_command_id: str
    create_command_id: str
    edit_command_id: str
    delete_command_id: str
    scan_command_id: str = ""
    show_command_id: str = ""


MODEL_VIEW_SPEC = AiModelCollectionViewSpec(
    action_id="ai_model_manager.models",
    view_id="ai_model_manager.models.view",
    object_type="gguf_model",
    singular_label="GGUF Model",
    plural_label="GGUF Models",
    description="Inspect GGUF model metadata, record sizes, and keep local model records in sync.",
    schema=build_collection_view_schema(
        GGUFModelRecord,
        list_fields=(
            "name",
            "local_path",
            "file_size_bytes",
            "size_class",
            "seats",
            "vision_enabled",
            "cost_mode",
            "input_token_cost_per_1k",
            "output_token_cost_per_1k",
        ),
        create_fields=(
            "name",
            "local_path",
            "file_size_bytes",
            "size_class",
            "seats",
            "cost_mode",
            "input_token_cost_per_1k",
            "output_token_cost_per_1k",
            "notes",
        ),
        edit_fields=(
            "name",
            "local_path",
            "file_size_bytes",
            "size_class",
            "seats",
            "cost_mode",
            "input_token_cost_per_1k",
            "output_token_cost_per_1k",
            "notes",
        ),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "metadata": {"hidden": True},
            "local_path": {
                "label": "Local path",
                "placeholder": "/models/llama-3.1-8b-instruct.gguf",
                "help_text": "Absolute or workspace-relative GGUF path.",
            },
            "file_size_bytes": {
                "label": "File size bytes",
                "min_value": 0,
                "step": 1,
                "help_text": "Usually filled by GGUF scanning.",
            },
            "size_class": {
                "label": "Size class",
                "placeholder": "small",
                "help_text": (
                    "Size buckets: small (<40 GB, many models on the AI PC or more on the server), "
                    "medium (40-85 GB, one model on the AI PC), "
                    "large (85-256 GB, CPU-bound only on the server), "
                    "xlarge (256-512 GB, one model this large on the server)."
                ),
            },
            "seats": {
                "label": "Seats",
                "field_type": "number",
                "min_value": 1,
                "step": 1,
                "default": 1,
                "help_text": "Number of concurrent user seats this model runtime supports. Reserved seats protect interactive users from background work.",
            },
            "vision_enabled": {
                "label": "Vision",
                "help_text": "Shows whether a matching mmproj companion was discovered in the same directory.",
            },
            "cost_mode": {
                "label": "Cost mode",
                "field_type": "select",
                "options": ["free", "metered", "hybrid", "unknown"],
                "default": "free",
            },
            "input_token_cost_per_1k": {
                "label": "Input token cost / 1k",
                "field_type": "text",
                "placeholder": "0.0005",
            },
            "output_token_cost_per_1k": {
                "label": "Output token cost / 1k",
                "field_type": "text",
                "placeholder": "0.0010",
            },
            "notes": {"field_type": "textarea", "help_text": "Optional internal notes."},
        },
        create={
            "title": "Add GGUF model",
            "description": "Record a local GGUF model and its initial estimates.",
            "submit_label": "Save model",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_manager.models.list",
    create_command_id="ai_model_manager.models.create",
    edit_command_id="ai_model_manager.models.edit",
    delete_command_id="ai_model_manager.models.delete",
    scan_command_id="ai_model_manager.models.scan",
    show_command_id="ai_model_manager.models.show",
)


PREFERENCE_VIEW_SPEC = AiModelCollectionViewSpec(
    action_id="ai_model_manager.preferences",
    view_id="ai_model_manager.preferences.view",
    object_type="task_preference",
    singular_label="Task Preference",
    plural_label="Task Preferences",
    description="Store task-to-model-size preferences for routing work to suitable model sizes.",
    schema=build_collection_view_schema(
        TaskSizePreference,
        list_fields=("task_name", "preferred_size_classes", "notes"),
        create_fields=("task_name", "preferred_size_classes", "notes"),
        edit_fields=("task_name", "preferred_size_classes", "notes"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "task_name": {
                "label": "Task name",
                "placeholder": "coding assistant",
                "help_text": "A stable label for the task or workflow.",
            },
            "preferred_size_classes": {
                "label": "Preferred size classes",
                "field_type": "text",
                "placeholder": "small, medium, 7B",
                "help_text": "Comma-separated preferred size classes, ordered by preference.",
            },
            "notes": {"field_type": "textarea", "help_text": "Optional routing notes."},
        },
        create={
            "title": "Add task preference",
            "description": "Capture preferred model sizes for a task.",
            "submit_label": "Save preference",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_manager.preferences.list",
    create_command_id="ai_model_manager.preferences.create",
    edit_command_id="ai_model_manager.preferences.edit",
    delete_command_id="ai_model_manager.preferences.delete",
)

LLM_CONFIG_VIEW_SPEC = AiModelCollectionViewSpec(
    action_id="ai_model_manager.llm_configs",
    view_id="ai_model_manager.llm_configs.view",
    object_type="llm_config",
    singular_label="LLM Config",
    plural_label="LLM Configs",
    description="Manage remote LLM endpoint configurations (OpenAI-compatible APIs).",
    schema=build_collection_view_schema(
        LLMConfig,
        list_fields=(
            "user_alias",
            "backend",
            "provider_name",
            "model_url",
            "max_response_size",
            "seats",
        ),
        create_fields=(
            "user_alias",
            "backend",
            "provider_name",
            "model_url",
            "api_key",
            "max_response_size",
            "seats",
            "system_prompt",
        ),
        edit_fields=(
            "user_alias",
            "backend",
            "provider_name",
            "model_url",
            "api_key",
            "max_response_size",
            "seats",
            "system_prompt",
        ),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "metadata": {"hidden": True},
            "user_alias": {
                "label": "Alias",
                "placeholder": "My Model",
                "help_text": "A friendly name for this model.",
            },
            "backend": {
                "label": "Backend",
                "field_type": "select",
                "options": ["openai_compatible"],
                "default": "openai_compatible",
            },
            "provider_name": {
                "label": "Provider name",
                "placeholder": "llama-3.1-8b",
                "help_text": "The model identifier used by the provider.",
            },
            "model_url": {
                "label": "API URL",
                "placeholder": "https://api.example.com/v1",
                "help_text": "Base URL for the OpenAI-compatible API.",
            },
            "api_key": {
                "label": "API key",
                "field_type": "password",
                "help_text": "API key for authentication (leave blank to keep existing).",
            },
            "max_response_size": {
                "label": "Max response size",
                "field_type": "number",
                "min_value": 1,
                "step": 1,
                "default": 8192,
                "help_text": "Maximum tokens in the response.",
            },
            "seats": {
                "label": "Seats",
                "field_type": "number",
                "min_value": 1,
                "step": 1,
                "default": 1,
                "help_text": "Number of concurrent user seats this endpoint supports. Reserved seats protect interactive users from background work.",
            },
            "system_prompt": {
                "label": "System prompt",
                "field_type": "textarea",
                "help_text": "Default system prompt for this model.",
            },
        },
        create={
            "title": "Add LLM Config",
            "description": "Add a remote LLM endpoint configuration.",
            "submit_label": "Save config",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_manager.llm_configs.list",
    create_command_id="ai_model_manager.llm_configs.create",
    edit_command_id="ai_model_manager.llm_configs.edit",
    delete_command_id="ai_model_manager.llm_configs.delete",
)


AI_MODEL_COLLECTION_VIEW_SPECS: tuple[AiModelCollectionViewSpec, ...] = (
    MODEL_VIEW_SPEC,
    PREFERENCE_VIEW_SPEC,
    LLM_CONFIG_VIEW_SPEC,
)
