from __future__ import annotations

from apmatia.core.registry import ViewContribution
from apmatia.core.view_contract.models import (
    ViewComponent,
    ViewBinding,
    ViewCondition,
    ViewDataSource,
    ViewStateDefinition,
    ViewAction,
    ViewEffect,
    ViewRefreshPolicy,
)

# Preferences form fields
_PREFERENCES_FORM_FIELDS = (
    ViewComponent(
        component_id="pref-llama-server-log-dir-field",
        component_type="field",
        properties={"label": "llama.cpp log directory", "field_type": "text", "help_text": "Directory containing llama.cpp server log files. Leave blank to use an environment override."},
    ),
    ViewComponent(
        component_id="pref-llama-server-executable-path-field",
        component_type="field",
        properties={"label": "llama-server executable", "field_type": "text", "help_text": "Path to the local llama-server binary used for execution."},
    ),
    ViewComponent(
        component_id="pref-llama-server-default-args-field",
        component_type="field",
        properties={"label": "llama-server default args", "field_type": "textarea", "help_text": "One argument per line. These are passed to every local launch."},
    ),
    ViewComponent(
        component_id="pref-gguf-directories-field",
        component_type="field",
        properties={"label": "GGUF model libraries", "field_type": "textarea", "help_text": "Use one directory per line or separate them with commas. The scanner recurses through each library."},
    ),
    ViewComponent(
        component_id="pref-auto-scan-gguf-directory-field",
        component_type="field",
        properties={"label": "Auto-scan GGUF directories on save", "field_type": "checkbox", "default": True},
    ),
    ViewComponent(
        component_id="pref-workspace-root-field",
        component_type="field",
        properties={"label": "Workspace root", "field_type": "text"},
    ),
    ViewComponent(
        component_id="pref-knowledge-root-field",
        component_type="field",
        properties={"label": "Knowledge root", "field_type": "text"},
    ),
    ViewComponent(
        component_id="pref-timezone-field",
        component_type="field",
        properties={"label": "Alarm time zone", "field_type": "select", "default": "America/Phoenix", "options": ("America/Phoenix", "America/Denver", "America/Chicago", "America/New_York", "UTC")},
    ),
    ViewComponent(
        component_id="pref-theme-field",
        component_type="field",
        properties={"label": "Theme", "field_type": "select", "default": "dark", "options": ("dark", "light", "system")},
    ),
    ViewComponent(
        component_id="pref-font-family-field",
        component_type="field",
        properties={"label": "Font family", "field_type": "text", "default": "system-ui"},
    ),
    ViewComponent(
        component_id="pref-accent-color-field",
        component_type="field",
        properties={"label": "Accent color", "field_type": "color", "default": "#ff6b6b"},
    ),
    ViewComponent(
        component_id="pref-font-size-field",
        component_type="field",
        properties={"label": "Font size", "field_type": "slider", "default": 16, "min_value": 12, "max_value": 24, "step": 1},
    ),
    ViewComponent(
        component_id="pref-title-bar-height-field",
        component_type="field",
        properties={"label": "Title bar height", "field_type": "slider", "default": 56, "min_value": 40, "max_value": 96, "step": 1},
    ),
    ViewComponent(
        component_id="pref-title-bar-font-size-field",
        component_type="field",
        properties={"label": "Title bar font size", "field_type": "slider", "default": 20, "min_value": 12, "max_value": 40, "step": 1},
    ),
    ViewComponent(
        component_id="pref-terminal-background-color-field",
        component_type="field",
        properties={"label": "Terminal background", "field_type": "color", "default": "#000000"},
    ),
    ViewComponent(
        component_id="pref-terminal-text-color-field",
        component_type="field",
        properties={"label": "Terminal text", "field_type": "color", "default": "#9dffad"},
    ),
    ViewComponent(
        component_id="pref-terminal-border-color-field",
        component_type="field",
        properties={"label": "Terminal border", "field_type": "text", "default": "rgba(110, 255, 170, 0.35)"},
    ),
    ViewComponent(
        component_id="pref-terminal-muted-color-field",
        component_type="field",
        properties={"label": "Terminal muted text", "field_type": "text", "default": "rgba(157, 255, 173, 0.72)"},
    ),
)

# Preferences view presentation tree
_PREFERENCES_PRESENTATION = ViewComponent(
    component_id="preferences-page",
    component_type="page",
    properties={"title": "Preferences", "caption": "Runtime, model discovery, roots, time zone, appearance, and terminal configuration."},
    children=(
        ViewComponent(
            component_id="preferences-form",
            component_type="form",
            properties={"title": "Preferences", "submit_label": "Save preferences"},
            children=_PREFERENCES_FORM_FIELDS,
            action_keys=("save",),
        ),
        ViewComponent(
            component_id="preferences-view-actions",
            component_type="actions",
            properties={"label": "Save preferences"},
            action_keys=("save",),
        ),
    ),
)

# Preferences view data sources
_PREFERENCES_DATA_SOURCES = ()

# Preferences view state
_PREFERENCES_STATE = (
    ViewStateDefinition(key="modified", value_type="boolean", default=False),
)

# Preferences view actions
_PREFERENCES_ACTIONS = (
    ViewAction(
        key="save",
        intent="save",
        label="Save preferences",
        scope="view",
        style="primary",
        operation="preferences:save",
        payload={"command_id": "preferences.save"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="modified", value=False),
            ViewEffect(effect_type="show_notification", value="Preferences saved"),
        ),
    ),
)

# Preferences view effects
_PREFERENCES_EFFECTS = ()

# Preferences view refresh policy
_PREFERENCES_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")

# Modules form fields
_MODULES_FORM_FIELDS = (
    ViewComponent(
        component_id="module-item-kind-field",
        component_type="field",
        properties={"label": "Type", "field_type": "hidden"},
    ),
    ViewComponent(
        component_id="module-module-id-field",
        component_type="field",
        properties={"label": "Module ID", "field_type": "hidden"},
    ),
    ViewComponent(
        component_id="module-view-id-field",
        component_type="field",
        properties={"label": "View ID", "field_type": "hidden"},
    ),
    ViewComponent(
        component_id="module-enabled-field",
        component_type="field",
        properties={"label": "Enable all modules", "field_type": "checkbox"},
    ),
    ViewComponent(
        component_id="module-hidden-field",
        component_type="field",
        properties={"label": "Hidden", "field_type": "checkbox"},
    ),
    ViewComponent(
        component_id="module-new-index-field",
        component_type="field",
        properties={"label": "Order (zero based)", "field_type": "number", "min_value": 0, "step": 1},
    ),
)

# Modules view presentation tree
_MODULES_PRESENTATION = ViewComponent(
    component_id="modules-page",
    component_type="page",
    properties={"title": "Modules", "caption": "Configure activation, visibility, and navigation order."},
    children=(
        ViewComponent(
            component_id="modules-collection",
            component_type="collection",
            binding=ViewBinding(source="modules", path="items"),
            children=(
                ViewComponent(
                    component_id="modules-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "item_kind", "label": "Type"},
                            {"key": "name", "label": "Name"},
                            {"key": "module_id", "label": "Module ID"},
                            {"key": "view_id", "label": "View ID"},
                            {"key": "enabled", "label": "Enabled"},
                            {"key": "hidden", "label": "Hidden"},
                            {"key": "new_index", "label": "Order"},
                        ],
                    },
                    action_keys=("edit",),
                ),
            ),
        ),
        ViewComponent(
            component_id="modules-edit-form",
            component_type="form",
            properties={"title": "Update catalog item", "submit_label": "Save"},
            children=_MODULES_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Modules view data sources
_MODULES_DATA_SOURCES = (
    ViewDataSource(
        key="modules",
        kind="collection",
        operation="preferences:list_catalog",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed", "include_empty": True},
    ),
)

# Modules view state
_MODULES_STATE = (
    ViewStateDefinition(key="selected_module_id", value_type="string", default=""),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Modules view actions
_MODULES_ACTIONS = (
    ViewAction(
        key="edit",
        intent="edit",
        label="Update",
        scope="item",
        operation="preferences:update_catalog_item",
        payload={"command_id": "preferences.update_catalog_item"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_module_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="preferences.modules.view"),
        ),
    ),
)

# Modules view effects
_MODULES_EFFECTS = ()

# Modules view refresh policy
_MODULES_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="preferences",
        action_id="preferences.preferences",
        view_id="preferences.preferences.view",
        name="Preferences",
        description="Configure Apmatia through the local API. Changes stay on this machine.",
        metadata={
            "view_contract_ready": True,
            "object_type": "preferences",
            "presentation": _PREFERENCES_PRESENTATION,
            "data_sources": _PREFERENCES_DATA_SOURCES,
            "state": _PREFERENCES_STATE,
            "actions": _PREFERENCES_ACTIONS,
            "effects": _PREFERENCES_EFFECTS,
            "refresh_policy": _PREFERENCES_REFRESH_POLICY,
        },
    ),
    ViewContribution(
        module_id="preferences",
        action_id="preferences.modules",
        view_id="preferences.modules.view",
        name="Modules",
        description="Configure module activation, visibility, and navigation order.",
        metadata={
            "view_contract_ready": True,
            "object_type": "module_catalog",
            "singular_label": "Module",
            "plural_label": "Modules",
            "empty_state": "No modules are registered yet.",
            "presentation": _MODULES_PRESENTATION,
            "data_sources": _MODULES_DATA_SOURCES,
            "state": _MODULES_STATE,
            "actions": _MODULES_ACTIONS,
            "effects": _MODULES_EFFECTS,
            "refresh_policy": _MODULES_REFRESH_POLICY,
        },
    ),
)
