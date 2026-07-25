from __future__ import annotations

import importlib
from unittest.mock import patch


def test_module_management_page_lists_modules(mock_streamlit):
    modules = [
        {
            "module_id": "ipe",
            "name": "Integrated Productivity Environment",
            "version": "0.1.0",
            "description": "Personal productivity tools.",
            "hidden": False,
            "view_count": 2,
            "visible_view_count": 1,
            "views": [
                {
                    "view_id": "ipe.task.view",
                    "name": "Tasks View",
                    "description": "Task collection.",
                    "hidden": False,
                    "effective_hidden": False,
                },
                {
                    "view_id": "ipe.project.view",
                    "name": "Projects View",
                    "description": "Project collection.",
                    "hidden": True,
                    "effective_hidden": True,
                },
            ],
        }
    ]

    with patch("apmatia.interfaces.streamlit.api_client.get_module_activation", return_value={"show_development_modules": False}), patch(
        "apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules
    ):
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_streamlit.title.assert_called_with("Module Management")
    mock_streamlit.subheader.assert_any_call("Integrated Productivity Environment")
    mock_streamlit.write.assert_any_call("Tasks View")
    mock_streamlit.write.assert_any_call("Projects View")


def test_module_management_page_toggles_module_visibility(mock_streamlit):
    modules = [
        {
            "module_id": "ipe",
            "name": "Integrated Productivity Environment",
            "version": "0.1.0",
            "description": "",
            "hidden": False,
            "view_count": 0,
            "visible_view_count": 0,
            "views": [],
        }
    ]
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide module"

    with patch("apmatia.interfaces.streamlit.api_client.get_module_activation", return_value={"show_development_modules": False}), patch(
        "apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules
    ), patch(
        "apmatia.interfaces.streamlit.api_client.set_module_visibility"
    ) as mock_set_module_visibility:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_module_visibility.assert_called_once_with("ipe", hidden=True)
    mock_streamlit.rerun.assert_called_once()


def test_module_management_page_reorders_modules(mock_streamlit):
    modules = [
        {"module_id": "ipe", "name": "Integrated Productivity Environment", "version": "0.1.0", "description": "", "hidden": False, "views": []},
        {"module_id": "worksim", "name": "Worksim", "version": "0.1.0", "description": "", "hidden": False, "views": []},
    ]
    mock_streamlit.button.side_effect = lambda label, **kwargs: label == "Move down" and not kwargs.get("disabled", False)

    with patch("apmatia.interfaces.streamlit.api_client.get_module_activation", return_value={"show_development_modules": False}), patch(
        "apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules
    ), patch(
        "apmatia.interfaces.streamlit.api_client.set_module_order"
    ) as mock_set_module_order:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_module_order.assert_called_once_with("ipe", new_index=1)
    mock_streamlit.rerun.assert_called_once()


def test_module_management_page_toggles_view_visibility(mock_streamlit):
    modules = [
        {
            "module_id": "ipe",
            "name": "Integrated Productivity Environment",
            "version": "0.1.0",
            "description": "",
            "hidden": False,
            "view_count": 1,
            "visible_view_count": 1,
            "views": [
                {
                    "view_id": "ipe.task.view",
                    "name": "Tasks View",
                    "description": "",
                    "hidden": False,
                    "effective_hidden": False,
                }
            ],
        }
    ]
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide view"

    with patch("apmatia.interfaces.streamlit.api_client.get_module_activation", return_value={"show_development_modules": False}), patch(
        "apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules
    ), patch(
        "apmatia.interfaces.streamlit.api_client.set_module_view_visibility"
    ) as mock_set_module_view_visibility:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_module_view_visibility.assert_called_once_with("ipe.task.view", hidden=True)
    mock_streamlit.rerun.assert_called_once()


def test_module_management_page_enables_all_modules(mock_streamlit):
    mock_streamlit.toggle.side_effect = None
    mock_streamlit.toggle.return_value = True

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_module_activation",
        return_value={"show_development_modules": False},
    ), patch(
        "apmatia.interfaces.streamlit.api_client.set_development_modules_enabled"
    ) as mock_set_development_modules_enabled:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_development_modules_enabled.assert_called_once_with(enabled=True)
    mock_streamlit.rerun.assert_called_once()
