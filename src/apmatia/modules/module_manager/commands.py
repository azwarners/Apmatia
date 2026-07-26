from __future__ import annotations

from apmatia.core.registry import CommandContribution


_COMMANDS = {
    "set_activation": "Set Module Activation",
    "set_module_visibility": "Set Module Visibility",
    "set_module_order": "Set Module Order",
    "set_view_visibility": "Set Module View Visibility",
    "set_view_order": "Set Module View Order",
}

_INPUT_FIELDS = {
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


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="module_manager",
        command_id=f"module_manager.{verb}",
        path=("module_manager", verb),
        name=name,
        description=f"{name} through the module manager.",
        metadata={"object_type": "module_catalog", "verb": verb, "input_fields": _INPUT_FIELDS[verb]},
    )
    for verb, name in _COMMANDS.items()
)
