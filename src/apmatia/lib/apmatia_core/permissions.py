from __future__ import annotations

from .models import ApmatiaObject


def _permission_mask(mode: int, shift: int) -> int:
    return (mode >> shift) & 0b111


def _permission_bits(obj: ApmatiaObject, user_id: int, group_ids: set[int]) -> int:
    if obj.owner_user_id is not None and user_id == obj.owner_user_id:
        return _permission_mask(obj.mode, 6)
    if obj.owner_group_id is not None and obj.owner_group_id in group_ids:
        return _permission_mask(obj.mode, 3) & 0b100
    return _permission_mask(obj.mode, 0)


def can_read(obj: ApmatiaObject, user_id: int, group_ids: set[int]) -> bool:
    return bool(_permission_bits(obj, user_id, group_ids) & 0b100)


def can_write(obj: ApmatiaObject, user_id: int, group_ids: set[int]) -> bool:
    return bool(_permission_bits(obj, user_id, group_ids) & 0b010)


def can_execute(obj: ApmatiaObject, user_id: int, group_ids: set[int]) -> bool:
    if obj.owner_user_id is not None and user_id == obj.owner_user_id:
        return bool(_permission_bits(obj, user_id, group_ids) & 0b001)
    if obj.owner_group_id is not None and obj.owner_group_id in group_ids:
        return False
    return True
