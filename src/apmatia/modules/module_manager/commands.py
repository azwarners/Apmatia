from __future__ import annotations

from apmatia.core.registry import CommandContribution


_COMMANDS = {
    "set_activation": "Set Module Activation",
    "set_module_visibility": "Set Module Visibility",
    "set_module_order": "Set Module Order",
    "set_view_visibility": "Set Module View Visibility",
    "set_view_order": "Set Module View Order",
}


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="module_manager",
        action_id="module_manager.module_manager",
        command_id=f"module_manager.module_manager.{verb}",
        path=("module_manager", "module_manager", verb),
        name=name,
        description=f"{name} through the module manager.",
        metadata={"object_type": "module_catalog", "verb": verb},
    )
    for verb, name in _COMMANDS.items()
)
