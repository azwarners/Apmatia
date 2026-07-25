from __future__ import annotations

from unittest.mock import patch

import pytest

from apmatia.core.module_management import (
    get_module_activation,
    list_module_catalog,
    set_development_modules_enabled,
    set_module_hidden,
    set_module_order,
    set_view_hidden,
)
from apmatia.core.registry import ModuleMetadata, ModuleStatus, Registry, ViewContribution


def _registry_with_modules() -> Registry:
    registry = Registry()
    registry.register_module(
        ModuleMetadata(
            module_id="ipe",
            name="Integrated Productivity Environment",
            version="0.1.0",
            description="Personal productivity tools.",
            status=ModuleStatus.STABLE,
        )
    )
    registry.register_module(
        ModuleMetadata(
            module_id="worksim",
            name="Worksim",
            version="0.1.0",
            description="A workplace simulation module centered on a persistent org chart wiki.",
            status=ModuleStatus.STABLE,
        )
    )
    registry.register_view(
        ViewContribution(
            module_id="ipe",
            action_id="ipe.task",
            view_id="ipe.task.view",
            name="Tasks View",
            description="Task collection.",
        )
    )
    registry.register_view(
        ViewContribution(
            module_id="ipe",
            action_id="ipe.project",
            view_id="ipe.project.view",
            name="Projects View",
            description="Project collection.",
        )
    )
    return registry


def test_list_module_catalog_combines_registry_and_hidden_settings():
    values = {
        ("ui", "hidden_module_ids"): ["ipe"],
        ("ui", "hidden_view_ids"): ["ipe.project.view"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ):
        catalog = list_module_catalog()

    assert [module["module_id"] for module in catalog] == ["ipe", "worksim"]
    ipe_module = catalog[0]
    assert ipe_module["hidden"] is True
    assert ipe_module["view_count"] == 2
    assert ipe_module["visible_view_count"] == 0
    assert [view["view_id"] for view in ipe_module["views"]] == [
        "ipe.project.view",
        "ipe.task.view",
    ]
    assert ipe_module["views"][0]["hidden"] is True
    assert ipe_module["views"][0]["effective_hidden"] is True
    assert ipe_module["views"][1]["hidden"] is False
    assert ipe_module["views"][1]["effective_hidden"] is True


def test_module_activation_defaults_to_stable_only():
    with patch("apmatia.core.module_management.get_config_value", return_value=False), patch(
        "apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()
    ):
        activation = get_module_activation()

    assert activation == {
        "show_development_modules": False,
        "active_module_ids": ["ipe", "worksim"],
    }


def test_enabling_development_modules_persists_and_refreshes_registry():
    with patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.refresh_application_registry"
    ) as mock_refresh_registry, patch(
        "apmatia.core.module_management.get_module_activation",
        return_value={"show_development_modules": True, "active_module_ids": ["example"]},
    ):
        activation = set_development_modules_enabled(True)

    mock_set_config_value.assert_called_once_with("ui", "show_development_modules", value=True)
    mock_refresh_registry.assert_called_once_with()
    assert activation["show_development_modules"] is True


def test_set_module_hidden_persists_sorted_unique_hidden_module_ids():
    values = {
        ("ui", "hidden_module_ids"): ["worksim", "worksim"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ), patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.get_module_catalog_entry",
        return_value={"module_id": "ipe", "hidden": True},
    ):
        result = set_module_hidden("ipe", hidden=True)

    mock_set_config_value.assert_called_once_with(
        "ui",
        "hidden_module_ids",
        value=["ipe", "worksim"],
    )
    assert result == {"module_id": "ipe", "hidden": True}


def test_list_module_catalog_applies_saved_module_order():
    values = {("ui", "module_orders"): ["worksim", "ipe"]}

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ):
        catalog = list_module_catalog()

    assert [module["module_id"] for module in catalog] == ["worksim", "ipe"]
    assert [module["sort_order"] for module in catalog] == [0, 1]


def test_set_module_order_persists_order_and_returns_module():
    values = {("ui", "module_orders"): []}

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ), patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.get_module_catalog_entry", return_value={"module_id": "worksim"}
    ):
        result = set_module_order("worksim", new_index=0)

    mock_set_config_value.assert_called_once_with("ui", "module_orders", value=["worksim", "ipe"])
    assert result == {"module_id": "worksim"}


def test_set_view_hidden_removes_view_from_hidden_list_when_showing():
    values = {
        ("ui", "hidden_view_ids"): ["ipe.task.view", "ipe.project.view"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ), patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.get_view_catalog_entry",
        return_value={"view_id": "ipe.task.view", "hidden": False},
    ):
        result = set_view_hidden("ipe.task.view", hidden=False)

    mock_set_config_value.assert_called_once_with(
        "ui",
        "hidden_view_ids",
        value=["ipe.project.view"],
    )
    assert result == {"view_id": "ipe.task.view", "hidden": False}


@pytest.mark.parametrize(
    ("function_name", "identifier", "message"),
    [
        ("set_module_hidden", "missing.module", "Unknown module: missing.module"),
        ("set_view_hidden", "missing.view", "Unknown view: missing.view"),
    ],
)
def test_visibility_updates_reject_unknown_ids(function_name: str, identifier: str, message: str):
    function = {"set_module_hidden": set_module_hidden, "set_view_hidden": set_view_hidden}[function_name]

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()):
        with pytest.raises(ValueError, match=message):
            function(identifier, hidden=True)
