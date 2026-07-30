from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from apmatia.core.registry.views import ViewContribution
from apmatia.core.view_contract import (
    VIEW_CONTRACT_VERSION,
    LEGACY_ADAPTER_FIELD_INVENTORY,
    RendererCapabilities,
    ViewAction,
    ViewBinding,
    ViewComponent,
    ViewContractValidationError,
    ViewContractCompatibilityError,
    ViewDataSource,
    ViewDocument,
    ViewEffect,
    ViewRefreshPolicy,
    ViewStateDefinition,
    normalize_view_document,
    negotiate_view_contract,
    validate_view_document,
)


def _legacy_view() -> ViewContribution:
    return ViewContribution(
        module_id="example",
        action_id="example.items",
        view_id="example.items.view",
        name="Items",
        description="Manage example items.",
        metadata={
            "singular_label": "Item",
            "plural_label": "Items",
            "commands": {
                "create": "example.items.create",
                "edit": "example.items.edit",
                "delete": "example.items.delete",
            },
            "schema": {
                "fields": [
                    {"key": "name", "label": "Name", "list": True, "create": True, "edit": True},
                    {
                        "key": "details",
                        "label": "Details",
                        "field_type": "textarea",
                        "create": True,
                        "edit": True,
                    },
                ]
            },
            "ui": {"render_mode": "collection", "caption": "Portable legacy metadata."},
        },
    )


def test_normalize_legacy_view_builds_serializable_versioned_document():
    document = normalize_view_document(_legacy_view())

    assert document.schema_version == VIEW_CONTRACT_VERSION
    assert document.module_id == "example"
    assert document.view_id == "example.items.view"
    assert document.presentation is not None
    assert document.presentation.component_type == "page"
    assert [child.component_type for child in document.presentation.children] == ["table", "form", "form"]
    assert document.data_sources[0].key == "items"
    assert [action.command_id for action in document.actions] == [
        "example.items.create",
        "example.items.edit",
        "example.items.delete",
    ]
    assert json.loads(json.dumps(document.to_dict()))["view_id"] == "example.items.view"


def test_view_document_serializes_non_json_defaults():
    view = _legacy_view()
    view.metadata["schema"]["fields"][0]["default"] = datetime(2026, 7, 26, 12, 30, tzinfo=timezone.utc)

    payload = normalize_view_document(view).to_dict()

    assert json.loads(json.dumps(payload))["presentation"]["children"][1]["children"][0]["properties"]["default"] == (
        "2026-07-26T12:30:00+00:00"
    )


def test_legacy_adapter_field_inventory_is_exhaustive_and_deterministic():
    assert LEGACY_ADAPTER_FIELD_INVENTORY == {
        "view": frozenset({"module_id", "view_id", "name", "description", "metadata"}),
        "metadata": frozenset(
            {"ui", "plural_label", "singular_label", "empty_state", "schema", "commands", "view_contract"}
        ),
        "view_contract": frozenset({"data_sources", "field_option_sources"}),
        "portable_data_source": frozenset(
            {
                "key", "kind", "operation", "parameters", "depends_on", "projection", "item_key",
                "loading_text", "empty_text", "error_text",
            }
        ),
        "ui": frozenset(
            {
                "render_mode", "layout", "renderer", "title", "caption", "empty_state", "item_key",
                "columns", "fields", "item_actions", "view_actions", "commands", "create_form",
                "edit_form", "form", "nav_pane",
            }
        ),
        "column": frozenset({"key", "source", "label", "empty_value"}),
        "action": frozenset({"key", "intent", "label", "scope", "style", "confirmation", "payload"}),
        "form": frozenset({"key", "title", "description", "submit_label", "cancel_label", "actions", "fields"}),
        "form_action": frozenset({"key", "intent", "label", "style", "payload"}),
        "field": frozenset(
            {
                "key", "label", "section", "field_type", "type", "input", "help_text", "help",
                "placeholder", "default", "required", "min_value", "max_value", "step", "options",
                "list", "create", "edit", "empty_value",
            }
        ),
        "nav_pane": frozenset(
            {
                "title", "top_exit_label", "bottom_exit_label", "empty_state", "item_label_key",
                "item_subtitle_key", "item_detail_key", "item_value_key",
            }
        ),
        "schema": frozenset({"version", "fields", "create", "edit", "resources"}),
        "schema_section": frozenset(
            {"key", "title", "description", "submit_label", "cancel_label", "actions", "fields", "extra_fields"}
        ),
        "commands": frozenset({"list", "create", "edit", "delete"}),
    }


def test_contract_accepts_rich_live_view_components():
    document = ViewDocument(
        view_id="example.discussion.view",
        module_id="example",
        title="Discussion",
        presentation=ViewComponent(
            component_id="discussion-page",
            component_type="page",
            children=(
                ViewComponent(
                    component_id="messages",
                    component_type="timeline",
                    binding=ViewBinding(source="messages"),
                    children=(ViewComponent(component_id="composer", component_type="composer"),),
                ),
                ViewComponent(component_id="activity", component_type="terminal"),
            ),
        ),
        data_sources=(ViewDataSource(key="messages", kind="stream", operation="discussion.messages"),),
        state=(ViewStateDefinition(key="active_discussion_id", scope="session"),),
        actions=(
            ViewAction(
                key="send",
                intent="send_message",
                label="Send",
                operation="discussion.prompt",
                success_effects=(ViewEffect(effect_type="refresh_source", target="messages"),),
            ),
        ),
    )

    assert validate_view_document(document) is document


def test_declared_contract_objects_survive_normalization_and_json_round_trip():
    view = ViewContribution(
        module_id="example",
        action_id="example.rich",
        view_id="example.rich.view",
        name="Rich",
        description="All first-class contract fields.",
        metadata={
            "view_contract_ready": True,
            "presentation": ViewComponent(
                component_id="rich-page",
                component_type="page",
                children=(
                    ViewComponent(
                        component_id="rich-field",
                        component_type="field",
                        properties={"key": "prompt", "field_type": "text"},
                    ),
                ),
            ),
            "data_sources": (
                ViewDataSource(key="items", operation="example.items", kind="collection"),
            ),
            "state": (ViewStateDefinition(key="selected", value_type="string", scope="session"),),
            "actions": (
                ViewAction(key="save", intent="save", label="Save", scope="form", operation="example.save"),
            ),
            "effects": (ViewEffect(effect_type="refresh_source", target="items"),),
            "refresh_policy": ViewRefreshPolicy(mode="on_intent"),
        },
    )

    document = normalize_view_document(view)
    restored = json.loads(json.dumps(document.to_dict()))

    assert document.presentation is not None
    assert document.presentation.children[0].properties["key"] == "prompt"
    assert document.data_sources[0].operation == "example.items"
    assert document.state[0].key == "selected"
    assert document.actions[0].operation == "example.save"
    assert document.effects[0].target == "items"
    assert document.refresh_policy.mode == "on_intent"
    assert restored["presentation"]["children"][0]["properties"]["key"] == "prompt"


def test_contract_validation_reports_precise_component_path():
    document = ViewDocument(
        view_id="example.invalid.view",
        module_id="example",
        title="Invalid",
        presentation=ViewComponent(
            component_id="root",
            component_type="page",
            children=(
                ViewComponent(component_id="duplicate", component_type="card"),
                ViewComponent(component_id="duplicate", component_type="unknown-widget"),
            ),
        ),
    )

    with pytest.raises(ViewContractValidationError) as captured:
        validate_view_document(document)

    message = str(captured.value)
    assert "views[example.invalid.view].presentation.children[1].component_id" in message
    assert "duplicate component ID: duplicate" in message
    assert "views[example.invalid.view].presentation.children[1].component_type" in message


def test_renderer_negotiation_reports_version_and_component_incompatibility():
    document = normalize_view_document(_legacy_view())
    renderer = RendererCapabilities(
        renderer_id="minimal",
        component_types=frozenset({"page", "form", "field"}),
    )

    with pytest.raises(ViewContractCompatibilityError) as captured:
        negotiate_view_contract(document, renderer)

    assert "views[example.items.view].presentation.children[0].component_type" in str(captured.value)
    assert "does not support table" in str(captured.value)

    future_document = ViewDocument(
        view_id="example.future.view",
        module_id="example",
        title="Future",
        schema_version=2,
        presentation=ViewComponent(component_id="root", component_type="page"),
    )
    with pytest.raises(ViewContractCompatibilityError, match=r"supports \(1,\), not 2"):
        negotiate_view_contract(future_document, RendererCapabilities(renderer_id="v1"))


def test_view_contract_import_does_not_require_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from apmatia.core.view_contract import normalize_view_document
from apmatia.core.registry.views import ViewContribution

document = normalize_view_document(ViewContribution(
    module_id="example",
    action_id="example.items",
    view_id="example.items.view",
    name="Items",
))
assert document.view_id == "example.items.view"
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
