"""Tests for API-owned portable view data sources."""

from unittest.mock import patch

from apmatia.api.internal.view_sources import load_view_source


def test_preferences_catalog_source_uses_the_preferences_view_provider() -> None:
    catalog = [{"id": "module:preferences", "item_kind": "module"}]

    with patch(
        "apmatia.api.internal.view_sources.get_module_view_items",
        return_value=catalog,
    ) as list_items:
        result = load_view_source("preferences:list_catalog", user_id=7)

    list_items.assert_called_once_with("preferences.modules.view", user_id=7)
    assert result == catalog
