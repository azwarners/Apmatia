from __future__ import annotations

import importlib

from apmatia.core.registry import ViewContribution
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.models import (
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
)


def _collection_view() -> ViewContribution:
    return ViewContribution(
        module_id="example",
        action_id="example.collection",
        view_id="example.collection.view",
        name="Example Collection",
        description="A generic collection view.",
        metadata={
            "ui": {
                "render_mode": "collection",
                "title": "Examples",
                "caption": "Rendered through the Streamlit adapter.",
                "empty_state": "No examples yet.",
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "status", "label": "Status"},
                ],
                "view_actions": [
                    {"key": "create", "label": "Create item", "intent": "create", "scope": "view", "style": "primary"},
                ],
                "item_actions": [
                    {"key": "edit", "label": "Edit", "intent": "edit", "scope": "item"},
                    {"key": "delete", "label": "Delete", "intent": "delete", "scope": "item"},
                ],
            }
        },
    )


def test_adapt_module_view_builds_collection_render_model():
    spec = adapt_module_view(
        _collection_view(),
        items=[{"id": 1, "name": "Alpha", "status": "active"}],
    )

    assert spec.view_id == "example.collection.view"
    assert spec.title == "Examples"
    assert spec.caption == "Rendered through the Streamlit adapter."
    assert spec.empty_state == "No examples yet."
    assert [column.key for column in spec.columns] == ["name", "status"]
    assert [action.intent for action in spec.view_actions] == ["create"]
    assert [action.intent for action in spec.item_actions] == ["edit", "delete"]
    assert spec.create_form is None
    assert spec.items == ({"id": 1, "name": "Alpha", "status": "active"},)


def test_adapt_module_view_parses_optional_create_form():
    view = _collection_view()
    view.metadata["ui"]["create_form"] = {
        "key": "create_example",
        "title": "Create example",
        "submit_label": "Save example",
        "fields": [
            {"key": "name", "label": "Name"},
            {"key": "details", "label": "Details", "field_type": "textarea"},
        ],
    }

    spec = adapt_module_view(view, items=[])

    assert spec.create_form is not None
    assert spec.create_form.key == "create_example"
    assert spec.create_form.title == "Create example"
    assert spec.create_form.submit_label == "Save example"
    assert [field.key for field in spec.create_form.fields] == ["name", "details"]


def test_adapt_module_view_parses_create_form_actions():
    view = _collection_view()
    view.metadata["ui"]["create_form"] = {
        "key": "create_example",
        "title": "Create example",
        "actions": [
            {
                "key": "prepare_ssh_key",
                "label": "Generate key",
                "intent": "prepare_ssh_key",
                "style": "secondary",
            }
        ],
        "fields": [
            {"key": "name", "label": "Name"},
        ],
    }

    spec = adapt_module_view(view, items=[])

    assert spec.create_form is not None
    assert [action.key for action in spec.create_form.actions] == ["prepare_ssh_key"]


def test_adapt_module_view_infers_columns_and_create_form_from_schema():
    view = _collection_view()
    view.metadata["ui"].pop("columns", None)
    view.metadata["schema"] = {
        "fields": [
            {"key": "name", "label": "Name", "list": True, "create": True, "edit": True},
            {"key": "details", "label": "Details", "list": True, "create": True, "edit": True, "field_type": "textarea"},
            {"key": "created_at", "label": "Created", "list": True, "create": False, "edit": False},
        ],
        "create": {
            "key": "create_example",
            "title": "Create example",
            "submit_label": "Save example",
        },
    }

    spec = adapt_module_view(view, items=[])

    assert [column.key for column in spec.columns] == ["name", "details", "created_at"]
    assert spec.create_form is not None
    assert spec.create_form.key == "create_example"
    assert spec.create_form.title == "Create example"
    assert [field.key for field in spec.create_form.fields] == ["name", "details"]
    assert spec.edit_form is not None
    assert spec.edit_form.key == "edit"
    assert spec.edit_form.title == "Edit example"
    assert [field.key for field in spec.edit_form.fields] == ["name", "details"]


def test_adapt_module_view_supports_existing_registry_collection_shape():
    view = ViewContribution(
        module_id="example",
        action_id="example.tasks",
        view_id="example.tasks.view",
        name="Tasks View",
        description="Track actionable work.",
        metadata={
            "object_type": "task",
            "singular_label": "Task",
            "plural_label": "Tasks",
            "empty_state": "No tasks yet.",
            "commands": {
                "list": "example.tasks.list",
                "create": "example.tasks.create",
                "edit": "example.tasks.edit",
                "delete": "example.tasks.delete",
            },
            "ui": {
                "render_mode": "collection",
                "layout": "table-with-actions",
            },
        },
    )

    spec = adapt_module_view(
        view,
        items=[{"id": 1, "title": "Ship adapter", "status": "todo"}],
    )

    assert spec.title == "Tasks"
    assert spec.empty_state == "No tasks yet."
    assert [column.key for column in spec.columns] == ["title", "status"]
    assert [action.intent for action in spec.view_actions] == ["create"]
    assert [action.intent for action in spec.item_actions] == ["edit", "delete"]
    assert spec.view_actions[0].payload == {"command_id": "example.tasks.create"}
    assert spec.item_actions[1].payload == {"command_id": "example.tasks.delete"}
    assert spec.item_actions[1].confirmation is True


def test_adapt_module_view_uses_ui_commands_when_present():
    view = ViewContribution(
        module_id="example",
        action_id="example.participants",
        view_id="example.participants.view",
        name="Chat Targets View",
        description="Track participants.",
        metadata={
            "object_type": "participant",
            "plural_label": "Participants",
            "ui": {
                "render_mode": "collection",
                "commands": {
                    "create": "example.participants.create",
                    "edit": "example.participants.edit",
                    "delete": "example.participants.delete",
                },
            },
        },
    )

    spec = adapt_module_view(view, items=[])

    assert [action.intent for action in spec.view_actions] == ["create"]
    assert [action.intent for action in spec.item_actions] == ["edit", "delete"]
    assert spec.view_actions[0].payload == {"command_id": "example.participants.create"}


def test_render_module_view_renders_empty_state(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)

    spec = adapt_module_view(_collection_view(), items=[])

    intents = renderers.render_module_view(spec)

    assert intents == []
    mock_streamlit.title.assert_called_with("Examples")
    mock_streamlit.caption.assert_called_with("Rendered through the Streamlit adapter.")
    mock_streamlit.info.assert_called_with("No examples yet.")


def test_render_module_view_renders_rows_and_emits_intents(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)

    mock_streamlit.button.side_effect = [True, True, False]

    spec = adapt_module_view(
        _collection_view(),
        items=[{"id": 1, "name": "Alpha", "status": "active"}],
    )

    received: list[ModuleViewIntent] = []
    intents = renderers.render_module_view(spec, on_intent=received.append)

    assert len(intents) == 2
    assert [intent.intent for intent in intents] == ["create", "edit"]
    assert [intent.action_key for intent in received] == ["create", "edit"]
    mock_streamlit.button.assert_any_call(
        "Create item",
        key="view-example.collection.view-create",
        type="primary",
        disabled=False,
        use_container_width=True,
    )
    mock_streamlit.button.assert_any_call(
        "Edit",
        key="example.collection.view-1-edit",
        type="secondary",
        disabled=False,
        use_container_width=True,
    )
    mock_streamlit.button.assert_any_call(
        "Delete",
        key="example.collection.view-1-delete",
        type="secondary",
        disabled=False,
        use_container_width=True,
    )


def test_render_module_view_renders_troubleshooting_footer(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)

    spec = adapt_module_view(
        _collection_view(),
        items=[
            {
                "id": 1,
                "name": "Alpha",
                "status": "active",
                "host_summary": "ID 1 | Alpha | 192.168.86.132",
                "troubleshooting_hint": "The remote SSH session reached the host, but the remote command failed while resolving the session user. This is not a password prompt problem.",
                "resource_error": "SSH inspection failed: No user exists for uid 1000",
                "ssh_connection_test_command": "ssh -vvv nick@192.168.86.132",
                "ssh_public_key_install_command": "ssh-copy-id -i ~/.ssh/id_ed25519.pub nick@192.168.86.132",
            }
        ],
    )

    renderers.render_module_view(spec)

    mock_streamlit.subheader.assert_called_with("Troubleshooting")
    mock_streamlit.write.assert_any_call("ID 1 | Alpha | 192.168.86.132")
    mock_streamlit.write.assert_any_call(
        "The remote SSH session reached the host, but the remote command failed while resolving the session user. This is not a password prompt problem."
    )
    mock_streamlit.write.assert_any_call("SSH inspection failed: No user exists for uid 1000")
    mock_streamlit.caption.assert_any_call("Copy and run this from the machine running Apmatia to inspect the SSH handshake.")
    mock_streamlit.caption.assert_called_with("Copy and run this from the machine running Apmatia after the key has been created.")
    mock_streamlit.code.assert_any_call("ssh -vvv nick@192.168.86.132", language="bash")
    mock_streamlit.code.assert_called_with("ssh-copy-id -i ~/.ssh/id_ed25519.pub nick@192.168.86.132", language="bash")


def test_render_module_view_form_renders_action_button(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)
    mock_streamlit.form_submit_button.side_effect = [True, False, False]

    form = ModuleViewFormDescriptor(
        key="create_example",
        title="Create example",
        actions=(
            ModuleViewFormActionDescriptor(
                key="prepare_ssh_key",
                label="Generate/Prepare SSH key",
                intent="prepare_ssh_key",
            ),
        ),
        fields=(ModuleViewFormFieldDescriptor(key="name", label="Name"),),
    )

    submitted, cancelled, payload, action_key = renderers.render_module_view_form(form, form_key="form:key")

    assert submitted is False
    assert cancelled is False
    assert action_key == "prepare_ssh_key"
    assert payload["name"] == "testuser"


def test_render_module_view_gracefully_handles_unsupported_modes(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)

    view = ViewContribution(
        module_id="example",
        action_id="example.details",
        view_id="example.details.view",
        name="Example Details",
        description="Unsupported view type.",
        metadata={"ui": {"render_mode": "details"}},
    )

    spec = adapt_module_view(view, items=[{"id": 1}])
    intents = renderers.render_module_view(spec)

    assert intents == []
    mock_streamlit.warning.assert_called_with("Unsupported module view render mode: details")
