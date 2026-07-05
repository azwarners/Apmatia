from __future__ import annotations

import importlib
from unittest.mock import patch

from apmatia.interfaces.streamlit.module_views.models import (
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
)


def test_module_views_page_shows_help_when_no_view_is_bound(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    with patch.object(module_views_page, "list_modules", return_value=[]):
        module_views_page.render()

    mock_streamlit.title.assert_called_with("Module Views")
    mock_streamlit.info.assert_called()


def test_module_views_page_renders_selected_catalog_view(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

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
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

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
        module_views_page, "render_module_view_form", return_value=(True, False, {"title": "Alpha"}, None)
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "created"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.create", title="Alpha")
    assert mock_streamlit.session_state["module_view_create_open:example.collection.view"] is False
    mock_streamlit.success.assert_called_with("Item created.")
    mock_streamlit.rerun.assert_called()


def test_module_views_page_submits_edit_form(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_edit_target"] = {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.edit",
        "item": {"id": 1, "title": "Alpha", "details": "Old"},
    }
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
        edit_form=ModuleViewFormDescriptor(
            key="edit_example",
            title="Edit example",
            submit_label="Save changes",
            fields=(
                ModuleViewFormFieldDescriptor(key="title", label="Title"),
            ),
        ),
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "title": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "render_module_view_form", return_value=(True, False, {"title": "Alpha updated"}, None)
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "updated"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.edit", item_id=1, title="Alpha updated")
    assert "module_view_edit_target" not in mock_streamlit.session_state
    mock_streamlit.success.assert_called_with("Item updated.")
    mock_streamlit.rerun.assert_called()


def test_module_views_page_prepares_ssh_key_from_form_action(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_create_open:example.collection.view"] = True
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
            actions=(
                ModuleViewFormActionDescriptor(
                    key="prepare_ssh_key",
                    label="Generate/Prepare SSH key",
                    intent="prepare_ssh_key",
                    style="secondary",
                    payload={"command_id": "example.collection.prepare_ssh_key"},
                ),
            ),
            fields=(ModuleViewFormFieldDescriptor(key="credential_ref", label="Credential ref"),),
        ),
    )
    prepare_result = {
        "status": "prepared",
        "credential_ref": "~/.apmatia/ssh/id_ed25519",
        "private_key_path": "~/.apmatia/ssh/id_ed25519",
        "message": "SSH key prepared at ~/.apmatia/ssh/id_ed25519.",
        "ssh_public_key_install_command": "ssh-copy-id -i ~/.apmatia/ssh/id_ed25519.pub nick@192.168.86.132",
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page,
        "render_module_view_form",
        return_value=(False, False, {"credential_ref": ""}, "prepare_ssh_key"),
    ), patch.object(
        module_views_page, "execute_module_command", return_value=prepare_result
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.prepare_ssh_key", credential_ref="")
    assert mock_streamlit.session_state["module_view_create_draft:example.collection.view"]["credential_ref"] == "~/.apmatia/ssh/id_ed25519"
    assert mock_streamlit.session_state["module_view_create_notice:example.collection.view"]["message"] == "SSH key prepared at ~/.apmatia/ssh/id_ed25519."
    mock_streamlit.rerun.assert_called()


def test_module_views_page_prompts_before_deleting_item(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

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
        item_actions=(
            ModuleViewActionDescriptor(
                key="delete",
                label="Delete",
                intent="delete",
                scope="item",
                style="secondary",
                confirmation=True,
                payload={"command_id": "example.collection.delete"},
            ),
        ),
    )
    delete_intent = ModuleViewIntent(
        view_id="example.collection.view",
        intent="delete",
        action_key="delete",
        scope="item",
        item_id=1,
        item={"id": 1, "name": "Alpha"},
        payload={"command_id": "example.collection.delete"},
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[delete_intent]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "deleted"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_not_called()
    assert mock_streamlit.session_state["module_view_delete_target"] == {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.delete",
    }
    mock_streamlit.rerun.assert_called()


def test_module_views_page_confirms_delete_item(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_delete_target"] = {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.delete",
    }
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
    )
    mock_streamlit.button.side_effect = lambda label, **kwargs: label == "Delete" and kwargs.get("key") == "confirm_delete_module_view:example.collection.view:1"

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "deleted"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.delete", item_id=1)
    assert "module_view_delete_target" not in mock_streamlit.session_state
    mock_streamlit.success.assert_called_with("Item deleted.")
    mock_streamlit.rerun.assert_called()
