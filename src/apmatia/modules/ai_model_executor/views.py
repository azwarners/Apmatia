from __future__ import annotations

from apmatia.core.registry import ViewContribution

from .collections import AI_MODEL_EXECUTOR_COLLECTION_VIEW_SPECS


def _build_view_spec(spec):
    """Build a ViewContribution from a collection view spec."""
    # Build columns for the UI
    columns = []
    for field in spec.schema.get("fields", []):
        if field.get("list", False):
            label = field.get("label", field.get("key", ""))
            columns.append({"key": field["key"], "label": label})

    # Build commands dict for the UI
    commands = {}
    if spec.list_command_id:
        commands["list"] = spec.list_command_id
    if spec.create_command_id:
        commands["create"] = spec.create_command_id
    if spec.edit_command_id:
        commands["edit"] = spec.edit_command_id
    if spec.delete_command_id:
        commands["delete"] = spec.delete_command_id
    if spec.show_command_id:
        commands["show"] = spec.show_command_id
    if spec.scan_command_id:
        commands["scan"] = spec.scan_command_id

    return ViewContribution(
        module_id="ai_model_executor",
        action_id=spec.action_id,
        view_id=spec.view_id,
        name=f"{spec.plural_label} View",
        description=spec.description,
        metadata={
            "ui": {
                "render_mode": "collection",
                "title": spec.plural_label.title(),
                "caption": spec.description,
                "empty_state": f"No {spec.plural_label.lower()} have been recorded yet.",
                "item_key": "id",
                "columns": columns,
                "commands": commands,
            },
            "schema": spec.schema,
            "object_type": spec.object_type,
            "singular_label": spec.singular_label,
            "plural_label": spec.plural_label,
            "empty_state": f"No {spec.plural_label.lower()} have been recorded yet.",
        },
    )


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = tuple(
    _build_view_spec(spec) for spec in AI_MODEL_EXECUTOR_COLLECTION_VIEW_SPECS
)
