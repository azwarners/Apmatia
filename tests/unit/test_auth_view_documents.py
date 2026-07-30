from __future__ import annotations

from unittest.mock import patch

from apmatia.api.internal.auth import list_auth_views
from apmatia.core.registry import Registry
from apmatia.modules.auth.views import VIEW_DESCRIPTORS


def test_public_auth_views_use_the_versioned_view_contract():
    registry = Registry()
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)

    with patch("apmatia.api.internal.auth.get_application_registry", return_value=registry):
        documents = list_auth_views()

    assert [document["view_id"] for document in documents] == ["auth.login.view", "auth.register.view"]
    assert all(document["schema_version"] == 1 for document in documents)
    assert all(document["presentation"]["component_type"] == "page" for document in documents)
    assert all("legacy_renderer" in document["metadata"] for document in documents)
