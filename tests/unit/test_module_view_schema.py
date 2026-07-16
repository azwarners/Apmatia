from __future__ import annotations

from apmatia.core.module_view_schema import build_collection_view_schema
from apmatia.modules.ipe.models import CapturedIdea


def test_build_collection_view_schema_infers_field_entries_from_dataclass():
    schema = build_collection_view_schema(
        CapturedIdea,
        list_fields=("title", "body", "captured_at"),
        create_fields=("title", "body", "tags"),
        create={"title": "Capture idea"},
        field_overrides={
            "body": {"field_type": "textarea", "label": "Details"},
            "tags": {"placeholder": "comma, separated, tags"},
        },
    )

    fields = {field["key"]: field for field in schema["fields"]}
    assert schema["version"] == 1
    assert schema["create"]["title"] == "Capture idea"
    assert fields["title"]["create"] is True
    assert fields["title"]["list"] is True
    assert fields["body"]["field_type"] == "textarea"
    assert fields["body"]["label"] == "Details"
    assert fields["captured_at"]["list"] is True
    assert fields["captured_at"]["create"] is False
    assert fields["source"]["default"] == "manual"
    assert fields["tags"]["placeholder"] == "comma, separated, tags"
