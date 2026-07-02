from __future__ import annotations

import importlib
from unittest.mock import patch


def test_module_management_page_lists_modules(mock_streamlit):
    modules = [
        {
            "module_id": "apmatia_ipe",
            "name": "Apmatia IPE",
            "version": "0.1.0",
            "description": "Personal productivity tools.",
            "hidden": False,
            "view_count": 2,
            "visible_view_count": 1,
            "views": [
                {
                    "view_id": "apmatia_ipe.task.view",
                    "name": "Tasks View",
                    "description": "Task collection.",
                    "hidden": False,
                    "effective_hidden": False,
                },
                {
                    "view_id": "apmatia_ipe.project.view",
                    "name": "Projects View",
                    "description": "Project collection.",
                    "hidden": True,
                    "effective_hidden": True,
                },
            ],
        }
    ]

    with patch("apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules):
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_streamlit.title.assert_called_with("Module Management")
    mock_streamlit.write.assert_any_call("**Apmatia IPE**")
    mock_streamlit.write.assert_any_call("Tasks View")
    mock_streamlit.write.assert_any_call("Projects View")


def test_module_management_page_toggles_module_visibility(mock_streamlit):
    modules = [
        {
            "module_id": "apmatia_ipe",
            "name": "Apmatia IPE",
            "version": "0.1.0",
            "description": "",
            "hidden": False,
            "view_count": 0,
            "visible_view_count": 0,
            "views": [],
        }
    ]
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide module"

    with patch("apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules), patch(
        "apmatia.interfaces.streamlit.api_client.set_module_visibility"
    ) as mock_set_module_visibility:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_module_visibility.assert_called_once_with("apmatia_ipe", hidden=True)
    mock_streamlit.rerun.assert_called_once()


def test_module_management_page_toggles_view_visibility(mock_streamlit):
    modules = [
        {
            "module_id": "apmatia_ipe",
            "name": "Apmatia IPE",
            "version": "0.1.0",
            "description": "",
            "hidden": False,
            "view_count": 1,
            "visible_view_count": 1,
            "views": [
                {
                    "view_id": "apmatia_ipe.task.view",
                    "name": "Tasks View",
                    "description": "",
                    "hidden": False,
                    "effective_hidden": False,
                }
            ],
        }
    ]
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide view"

    with patch("apmatia.interfaces.streamlit.api_client.list_modules", return_value=modules), patch(
        "apmatia.interfaces.streamlit.api_client.set_module_view_visibility"
    ) as mock_set_module_view_visibility:
        import apmatia.interfaces.streamlit.pages.module_management as module_management_page

        module_management_page = importlib.reload(module_management_page)
        module_management_page.render()

    mock_set_module_view_visibility.assert_called_once_with("apmatia_ipe.task.view", hidden=True)
    mock_streamlit.rerun.assert_called_once()
