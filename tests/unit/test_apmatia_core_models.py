"""Unit tests for the apmatia core object model."""

import pytest

from apmatia.lib.apmatia_core.models import ApmatiaObject
from apmatia.lib.apmatia_core.permissions import can_execute, can_read, can_write


class TestApmatiaObject:
    def test_create_default_object(self):
        obj = ApmatiaObject()

        assert obj.id is None
        assert obj.owner_user_id is None
        assert obj.owner_group_id is None
        assert obj.mode == 0o000
        assert obj.created_at.tzinfo is not None
        assert obj.updated_at.tzinfo is not None

    def test_accepts_string_ids_for_domain_objects(self):
        obj = ApmatiaObject(id="IDabc123")

        assert obj.id == "IDabc123"

    def test_permissions_respect_owner_group_and_other_bits(self):
        obj = ApmatiaObject(owner_user_id=10, owner_group_id=20, mode=0o754)

        assert can_read(obj, user_id=10, group_ids=set())
        assert can_write(obj, user_id=10, group_ids=set())
        assert can_execute(obj, user_id=10, group_ids=set())
        assert can_read(obj, user_id=99, group_ids={20})
        assert not can_write(obj, user_id=99, group_ids={20})
        assert not can_execute(obj, user_id=99, group_ids={20})
        assert can_read(obj, user_id=99, group_ids={88})
        assert not can_write(obj, user_id=99, group_ids={88})
        assert can_read(obj, user_id=99, group_ids=set())
        assert not can_write(obj, user_id=99, group_ids=set())
        assert can_execute(obj, user_id=99, group_ids=set())

    def test_rejects_out_of_range_modes(self):
        with pytest.raises(ValueError, match="mode must be between 000 and 777"):
            ApmatiaObject(mode=0o1000)
