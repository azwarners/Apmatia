from __future__ import annotations


# Exhaustive compatibility inventory for fields consumed by the pre-contract Streamlit adapter.
# Adding a legacy field requires updating this inventory and its contract documentation. New view
# work should use typed contract models instead of extending this compatibility surface.
LEGACY_ADAPTER_FIELD_INVENTORY: dict[str, frozenset[str]] = {
    "view": frozenset({"module_id", "view_id", "name", "description", "metadata"}),
    "metadata": frozenset(
        {"ui", "plural_label", "singular_label", "empty_state", "schema", "commands", "view_contract"}
    ),
    "view_contract": frozenset({"data_sources", "field_option_sources"}),
    "portable_data_source": frozenset(
        {
            "key",
            "kind",
            "operation",
            "parameters",
            "depends_on",
            "projection",
            "item_key",
            "loading_text",
            "empty_text",
            "error_text",
        }
    ),
    "ui": frozenset(
        {
            "render_mode",
            "layout",
            "renderer",
            "title",
            "caption",
            "empty_state",
            "item_key",
            "columns",
            "fields",
            "item_actions",
            "view_actions",
            "commands",
            "create_form",
            "edit_form",
            "form",
            "nav_pane",
        }
    ),
    "column": frozenset({"key", "source", "label", "empty_value"}),
    "action": frozenset({"key", "intent", "label", "scope", "style", "confirmation", "payload"}),
    "form": frozenset({"key", "title", "description", "submit_label", "cancel_label", "actions", "fields"}),
    "form_action": frozenset({"key", "intent", "label", "style", "payload"}),
    "field": frozenset(
        {
            "key",
            "label",
            "section",
            "field_type",
            "type",
            "input",
            "help_text",
            "help",
            "placeholder",
            "default",
            "required",
            "min_value",
            "max_value",
            "step",
            "options",
            "list",
            "create",
            "edit",
            "empty_value",
        }
    ),
    "nav_pane": frozenset(
        {
            "title",
            "top_exit_label",
            "bottom_exit_label",
            "empty_state",
            "item_label_key",
            "item_subtitle_key",
            "item_detail_key",
            "item_value_key",
        }
    ),
    "schema": frozenset({"version", "fields", "create", "edit", "resources"}),
    "schema_section": frozenset(
        {"key", "title", "description", "submit_label", "cancel_label", "actions", "fields", "extra_fields"}
    ),
    "commands": frozenset({"list", "create", "edit", "delete"}),
}


def legacy_adapter_field_inventory() -> dict[str, tuple[str, ...]]:
    """Return a deterministic, JSON-safe inventory for documentation and compatibility tests."""
    return {section: tuple(sorted(fields)) for section, fields in sorted(LEGACY_ADAPTER_FIELD_INVENTORY.items())}
