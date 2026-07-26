from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="module_manager",
        action_id="module_manager.module_manager",
        view_id="module_manager.module_manager.view",
        name="Module Manager",
        description="Configure module activation, visibility, and navigation order.",
        metadata={
            "object_type": "module_catalog",
            "singular_label": "Module",
            "plural_label": "Modules",
            "empty_state": "No modules are registered yet.",
            "commands": {
                verb: f"module_manager.{verb}"
                for verb in (
                    "set_activation",
                    "set_module_visibility",
                    "set_module_order",
                    "set_view_visibility",
                    "set_view_order",
                )
            },
            "ui": {
                "render_mode": "collection",
                "renderer": "module_manager",
                "title": "Module Manager",
            },
        },
    ),
)
