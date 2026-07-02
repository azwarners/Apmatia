from __future__ import annotations

from unittest.mock import patch

import pytest

from apmatia.core.module_management import list_module_catalog, set_module_hidden, set_view_hidden
from apmatia.core.registry import ModuleMetadata, Registry, ViewContribution


def _registry_with_modules() -> Registry:
    registry = Registry()
    registry.register_module(
        ModuleMetadata(
            module_id="apmatia_ipe",
            name="Apmatia IPE",
            version="0.1.0",
            description="Personal productivity tools.",
        )
    )
    registry.register_module(
        ModuleMetadata(
            module_id="apmatia_worksim",
            name="Apmatia Worksim",
            version="0.1.0",
            description="A workplace simulation module centered on a persistent org chart wiki.",
        )
    )
    registry.register_view(
        ViewContribution(
            module_id="apmatia_ipe",
            action_id="apmatia_ipe.task",
            view_id="apmatia_ipe.task.view",
            name="Tasks View",
            description="Task collection.",
        )
    )
    registry.register_view(
        ViewContribution(
            module_id="apmatia_ipe",
            action_id="apmatia_ipe.project",
            view_id="apmatia_ipe.project.view",
            name="Projects View",
            description="Project collection.",
        )
    )
    return registry


def test_list_module_catalog_combines_registry_and_hidden_settings():
    values = {
        ("ui", "hidden_module_ids"): ["apmatia_ipe"],
        ("ui", "hidden_view_ids"): ["apmatia_ipe.project.view"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ):
        catalog = list_module_catalog()

    assert [module["module_id"] for module in catalog] == ["apmatia_ipe", "apmatia_worksim"]
    ipe_module = catalog[0]
    assert ipe_module["hidden"] is True
    assert ipe_module["view_count"] == 2
    assert ipe_module["visible_view_count"] == 0
    assert [view["view_id"] for view in ipe_module["views"]] == [
        "apmatia_ipe.project.view",
        "apmatia_ipe.task.view",
    ]
    assert ipe_module["views"][0]["hidden"] is True
    assert ipe_module["views"][0]["effective_hidden"] is True
    assert ipe_module["views"][1]["hidden"] is False
    assert ipe_module["views"][1]["effective_hidden"] is True


def test_set_module_hidden_persists_sorted_unique_hidden_module_ids():
    values = {
        ("ui", "hidden_module_ids"): ["apmatia_worksim", "apmatia_worksim"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ), patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.get_module_catalog_entry",
        return_value={"module_id": "apmatia_ipe", "hidden": True},
    ):
        result = set_module_hidden("apmatia_ipe", hidden=True)

    mock_set_config_value.assert_called_once_with(
        "ui",
        "hidden_module_ids",
        value=["apmatia_ipe", "apmatia_worksim"],
    )
    assert result == {"module_id": "apmatia_ipe", "hidden": True}


def test_set_view_hidden_removes_view_from_hidden_list_when_showing():
    values = {
        ("ui", "hidden_view_ids"): ["apmatia_ipe.task.view", "apmatia_ipe.project.view"],
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.module_management.get_application_registry", return_value=_registry_with_modules()), patch(
        "apmatia.core.module_management.get_config_value", side_effect=fake_get_config_value
    ), patch("apmatia.core.module_management.set_config_value") as mock_set_config_value, patch(
        "apmatia.core.module_management.get_view_catalog_entry",
        return_value={"view_id": "apmatia_ipe.task.view", "hidden": False},
    ):
        result = set_view_hidden("apmatia_ipe.task.view", hidden=False)

    mock_set_config_value.assert_called_once_with(
        "ui",
        "hidden_view_ids",
        value=["apmatia_ipe.project.view"],
    )
    assert result == {"view_id": "apmatia_ipe.task.view", "hidden": False}


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
