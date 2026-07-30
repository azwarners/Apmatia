from __future__ import annotations

from apmatia.core.registry import CommandContribution


_MODULE_COMMANDS = {
    "update_catalog_item": "Update Module Catalog Item",
    "set_activation": "Set Module Activation",
    "set_module_visibility": "Set Module Visibility",
    "set_module_order": "Set Module Order",
    "set_view_visibility": "Set Module View Visibility",
    "set_view_order": "Set Module View Order",
}

_MODULE_INPUT_FIELDS = {
    "update_catalog_item": [],
    "set_activation": [{"key": "enabled", "data_type": "boolean", "required": True}],
    "set_module_visibility": [
        {"key": "module_id", "required": True},
        {"key": "hidden", "data_type": "boolean", "required": True},
    ],
    "set_module_order": [
        {"key": "module_id", "required": True},
        {"key": "new_index", "data_type": "number", "required": True},
    ],
    "set_view_visibility": [
        {"key": "view_id", "required": True},
        {"key": "hidden", "data_type": "boolean", "required": True},
    ],
    "set_view_order": [
        {"key": "module_id", "required": True},
        {"key": "view_id", "required": True},
        {"key": "new_index", "data_type": "number", "required": True},
    ],
}


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="preferences",
        command_id="preferences.save",
        path=("preferences", "save"),
        name="Save Preferences",
        description="Save Apmatia's local preferences.",
        metadata={"object_type": "preferences", "verb": "save"},
    ),
) + tuple(
    CommandContribution(
        module_id="preferences",
        command_id=f"preferences.{verb}",
        path=("preferences", verb),
        name=name,
        description=f"{name} through Preferences.",
        metadata={"object_type": "module_catalog", "verb": verb, "input_fields": _MODULE_INPUT_FIELDS[verb]},
    )
    for verb, name in _MODULE_COMMANDS.items()
)
