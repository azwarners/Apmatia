from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apmatia.api.http.app import create_app
from apmatia.api.http.routes import module_routes
from apmatia.api.internal.module_views import get_module_view_document, list_module_view_documents
from apmatia.core.registry import Registry


def _registry() -> Registry:
    registry = Registry()
    registry.register_view(
        module_id="example",
        action_id="example.items",
        view_id="example.items.view",
        name="Items",
        description="Portable items.",
        metadata={"ui": {"render_mode": "collection"}},
    )
    return registry


def test_internal_api_serializes_registered_view_documents():
    with patch("apmatia.api.internal.module_views.get_application_registry", return_value=_registry()):
        documents = list_module_view_documents()
        document = get_module_view_document("example.items.view")

    assert documents == [document]
    assert document["schema_version"] == 1
    assert document["view_id"] == "example.items.view"
    assert document["presentation"]["component_type"] == "page"


def test_internal_api_rejects_unknown_view_document():
    with patch("apmatia.api.internal.module_views.get_application_registry", return_value=_registry()):
        with pytest.raises(ValueError, match="Unknown module view: missing.view"):
            get_module_view_document("missing.view")


def test_http_api_requires_session_and_returns_document_catalog():
    request = SimpleNamespace()
    documents = [{"schema_version": 1, "view_id": "example.items.view"}]

    with patch("apmatia.api.http.routes.module_routes.require_session") as require_session, patch(
        "apmatia.api.http.routes.module_routes.list_module_view_documents",
        return_value=documents,
    ):
        result = module_routes.get_view_documents(request)

    require_session.assert_called_once_with(request)
    assert result == documents


def test_http_api_requires_session_and_returns_one_document():
    request = SimpleNamespace()
    document = {"schema_version": 1, "view_id": "example.items.view"}

    with patch("apmatia.api.http.routes.module_routes.require_session") as require_session, patch(
        "apmatia.api.http.routes.module_routes.get_module_view_document",
        return_value=document,
    ):
        result = module_routes.get_view_document(request, "example.items.view")

    require_session.assert_called_once_with(request)
    assert result == document


def test_http_api_returns_not_found_for_unknown_document():
    with patch("apmatia.api.http.routes.module_routes.require_session"), patch(
        "apmatia.api.http.routes.module_routes.get_module_view_document",
        side_effect=ValueError("Unknown module view: missing.view"),
    ):
        with pytest.raises(HTTPException) as error:
            module_routes.get_view_document(SimpleNamespace(), "missing.view")

    assert error.value.status_code == 404
    assert error.value.detail == "Unknown module view: missing.view"


def test_http_routes_serialize_catalog_and_individual_document():
    document = {"schema_version": 1, "view_id": "example.items.view", "presentation": {"component_type": "page"}}

    with patch("apmatia.api.http.routes.module_routes.require_session", return_value=SimpleNamespace(user_id=42)), patch(
        "apmatia.api.http.routes.module_routes.list_module_view_documents",
        return_value=[document],
    ), patch(
        "apmatia.api.http.routes.module_routes.get_module_view_document",
        return_value=document,
    ):
        client = TestClient(create_app())
        catalog_response = client.get("/api/module-view-documents")
        document_response = client.get("/api/module-views/example.items.view/document")

    assert catalog_response.status_code == 200
    assert catalog_response.json() == [document]
    assert document_response.status_code == 200
    assert document_response.json() == document
