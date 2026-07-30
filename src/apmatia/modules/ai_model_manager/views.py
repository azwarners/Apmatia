from __future__ import annotations

from apmatia.core.registry import ViewContribution

from .collections import AI_MODEL_COLLECTION_VIEW_SPECS

VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = tuple(
    ViewContribution(
        module_id="ai_model_manager",
        action_id=spec.action_id,
        view_id=spec.view_id,
        name=f"{spec.plural_label} View",
        description=spec.description,
        metadata={
            "view_contract_ready": True,
            "ui": {
                "render_mode": "collection",
                "title": spec.plural_label,
                "caption": spec.description,
                "empty_state": f"No {spec.plural_label.lower()} have been recorded yet.",
                "item_key": "id",
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "local_path", "label": "Local Path"},
                    {"key": "file_size_human", "label": "Size"},
                    {"key": "size_class", "label": "Size Class"},
                    {"key": "seats", "label": "Seats"},
                    {"key": "vision_enabled", "label": "Vision"},
                    {"key": "cost_mode", "label": "Cost"},
                ]
                if spec.object_type == "gguf_model"
                else [
                    {"key": "user_alias", "label": "Alias"},
                    {"key": "backend", "label": "Backend"},
                    {"key": "provider_name", "label": "Provider"},
                    {"key": "model_url", "label": "API URL"},
                    {"key": "max_response_size", "label": "Max Size"},
                    {"key": "seats", "label": "Seats"},
                ]
                if spec.object_type == "llm_config"
                else [
                    {"key": "task_name", "label": "Task"},
                    {"key": "preferred_size_classes", "label": "Preferred Sizes"},
                    {"key": "notes", "label": "Notes"},
                ],
                "commands": {
                    "create": spec.create_command_id,
                    "edit": spec.edit_command_id,
                    "delete": spec.delete_command_id,
                },
            },
            "schema": dict(spec.schema),
            "object_type": spec.object_type,
            "singular_label": spec.singular_label,
            "plural_label": spec.plural_label,
            "empty_state": f"No {spec.plural_label.lower()} have been recorded yet.",
        },
    )
    for spec in AI_MODEL_COLLECTION_VIEW_SPECS
)
