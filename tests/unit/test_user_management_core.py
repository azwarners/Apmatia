from src.lib.user_management.models import GroupRole
from src.lib.user_management.module import AccessController, GroupManager, UserManager
from src.lib.user_management.sqlite_repositories import SQLiteUserManagementBundle


def _bundle(tmp_path):
    db_path = tmp_path / "users.db"
    return SQLiteUserManagementBundle(db_path)


def test_user_crud_and_verify(tmp_path):
    bundle = _bundle(tmp_path)
    users = UserManager(bundle.users)

    created = users.create_user("nick", "pw123")
    assert created.id is not None
    assert created.username == "nick"
    assert created.password_hash != "pw123"

    assert users.verify_user("nick", "pw123") is True
    assert users.verify_user("nick", "wrong") is False

    edited = users.edit_user(created.id, username="nick2", password="pw456")
    assert edited.username == "nick2"
    assert users.verify_user("nick2", "pw456") is True
    assert users.verify_user("nick", "pw123") is False

    listed = users.list_users()
    assert len(listed) == 1
    assert listed[0].username == "nick2"

    assert users.delete_user(created.id) is True
    assert users.delete_user(created.id) is False
    assert users.list_users() == []


def test_group_and_membership_flow(tmp_path):
    bundle = _bundle(tmp_path)
    users = UserManager(bundle.users)
    groups = GroupManager(bundle.groups, bundle.memberships)
    acl = AccessController(bundle.memberships)

    owner = users.create_user("owner", "pw")
    member = users.create_user("member", "pw")

    group = groups.create_group("team", created_by_user_id=owner.id or 0, description="core team")
    assert group.id is not None
    assert group.name == "team"

    owner_memberships = groups.list_group_members(group.id or 0)
    assert len(owner_memberships) == 1
    assert owner_memberships[0].user_id == owner.id
    assert owner_memberships[0].role == GroupRole.OWNER

    new_membership = groups.add_member(group.id or 0, member.id or 0, role=GroupRole.MEMBER)
    assert new_membership.id is not None
    assert new_membership.user_id == member.id

    assert acl.can_read_group(group.id or 0, member.id or 0) is True
    assert acl.can_write_group(group.id or 0, member.id or 0) is True
    assert acl.can_read_private(owner.id or 0, owner.id or 0) is True
    assert acl.can_read_private(owner.id or 0, member.id or 0) is False

    assert groups.delete_group(group.id or 0) is True
    assert groups.delete_group(group.id or 0) is False

