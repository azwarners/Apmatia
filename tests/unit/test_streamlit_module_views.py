from __future__ import annotations

import importlib
from unittest.mock import patch

from src.interfaces.streamlit.module_views.models import (
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
)


def test_module_views_page_shows_help_when_no_view_is_bound(mock_streamlit):
    import src.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    with patch.object(module_views_page, "list_modules", return_value=[]):
        module_views_page.render()

    mock_streamlit.title.assert_called_with("Module Views")
    mock_streamlit.info.assert_called()


def test_module_views_page_renders_selected_catalog_view(mock_streamlit):
    import src.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ) as mock_list_items, patch.object(module_views_page, "render_module_view", return_value=[]) as mock_render:
        module_views_page.render()

    mock_list_items.assert_called_once_with("example.collection.view")
    mock_render.assert_called_once()


def test_module_views_page_submits_create_form(mock_streamlit):
    import src.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.collection.create"},
            ),
        ),
        create_form=ModuleViewFormDescriptor(
            key="create_example",
            title="Create example",
            submit_label="Save",
            fields=(
                ModuleViewFormFieldDescriptor(key="title", label="Title"),
            ),
        ),
    )
    create_intent = ModuleViewIntent(
        view_id="example.collection.view",
        intent="create",
        action_key="create",
        scope="view",
        payload={"command_id": "example.collection.create"},
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[create_intent]
    ), patch.object(
        module_views_page, "render_module_view_form", return_value=(True, False, {"title": "Alpha"})
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "created"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.create", title="Alpha")
    assert mock_streamlit.session_state["module_view_create_open:example.collection.view"] is False
    mock_streamlit.success.assert_called_with("Item created.")
    mock_streamlit.rerun.assert_called()
