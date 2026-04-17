import importlib

import pytest


def test_discussion_private_scope_is_per_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()

    snap_user_1 = state.snapshot(user_id=101, member_group_ids=set())
    snap_user_2 = state.snapshot(user_id=202, member_group_ids=set())

    assert snap_user_1.discussion_id != snap_user_2.discussion_id

    new_user_1_discussion = state.reset_discussion(user_id=101)
    assert new_user_1_discussion != snap_user_1.discussion_id
    assert state.snapshot(user_id=202, member_group_ids=set()).discussion_id == snap_user_2.discussion_id


def test_discussion_group_scope_is_shared(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    group_discussion = state.create_discussion(
        owner_user_id=101,
        title="Team Chat",
        group_id=55,
    )
    state.open_discussion(user_id=101, discussion_id=group_discussion["discussion_id"], member_group_ids={55})

    snap_from_user_1 = state.snapshot(user_id=101, member_group_ids={55})
    state.open_discussion(user_id=202, discussion_id=group_discussion["discussion_id"], member_group_ids={55})
    snap_from_user_2 = state.snapshot(user_id=202, member_group_ids={55})

    assert snap_from_user_1.discussion_id == snap_from_user_2.discussion_id

    state.set_system_prompt(user_id=101, member_group_ids={55}, system_prompt="group prompt")
    updated = state.snapshot(user_id=202, member_group_ids={55})
    assert updated.system_prompt == "group prompt"


def test_discussion_group_scope_blocks_non_members(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    group_discussion = state.create_discussion(
        owner_user_id=101,
        title="Restricted Team Chat",
        group_id=99,
    )

    try:
        state.open_discussion(
            user_id=202,
            discussion_id=group_discussion["discussion_id"],
            member_group_ids=set(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected non-member to be blocked from opening group discussion.")


def test_update_folder_prevents_descendant_cycles(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    folder_a = state.create_folder(owner_user_id=101, name="A")
    folder_b = state.create_folder(owner_user_id=101, name="B", parent_id=int(folder_a["id"]))

    with pytest.raises(ValueError, match="descendants"):
        state.update_folder(
            owner_user_id=101,
            folder_id=int(folder_a["id"]),
            parent_id=int(folder_b["id"]),
        )


def test_update_folder_allows_move_to_root(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    root = state.create_folder(owner_user_id=101, name="Root")
    child = state.create_folder(owner_user_id=101, name="Child", parent_id=int(root["id"]))

    updated = state.update_folder(
        owner_user_id=101,
        folder_id=int(child["id"]),
        parent_id=None,
    )

    assert updated["parent_id"] is None


def test_update_discussion_preserves_group_when_only_renaming(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(
        owner_user_id=101,
        title="Group Thread",
        group_id=55,
    )

    updated = state.update_discussion(
        owner_user_id=101,
        discussion_id=str(created["discussion_id"]),
        title="Renamed Group Thread",
    )

    assert updated["title"] == "Renamed Group Thread"
    assert updated["group_id"] == 55
    assert updated["visibility"] == "group"


def test_update_discussion_allows_move_to_root(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    folder = state.create_folder(owner_user_id=101, name="Folder")
    created = state.create_discussion(
        owner_user_id=101,
        title="Thread in Folder",
        folder_id=int(folder["id"]),
    )

    updated = state.update_discussion(
        owner_user_id=101,
        discussion_id=str(created["discussion_id"]),
        folder_id=None,
    )

    assert updated["folder_id"] is None


def test_snapshot_includes_parsed_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    snapshot = state.snapshot(user_id=101, member_group_ids=set())
    transcript_path = state._discussion_path(snapshot.discussion_id)
    transcript_path.write_text(
        "User: Hello there\nAssistant: Hi!\nHow can I help?\n",
        encoding="utf-8",
    )

    updated_snapshot = state.snapshot(user_id=101, member_group_ids=set())
    assert updated_snapshot.messages == [
        {"role": "User", "text": "Hello there"},
        {"role": "Assistant", "text": "Hi!\nHow can I help?"},
    ]


def test_reset_discussion_carries_system_prompt_forward(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    state.set_system_prompt(user_id=101, member_group_ids=set(), system_prompt="be concise")

    new_discussion_id = state.reset_discussion(user_id=101)
    snapshot = state.snapshot(user_id=101, member_group_ids=set())

    assert snapshot.discussion_id == new_discussion_id
    assert snapshot.system_prompt == "be concise"


def test_list_tree_creates_current_discussion_for_new_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.core.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    tree = state.list_tree(user_id=101, member_group_ids=set())

    assert tree["current_discussion_id"] is not None
    discussion_ids = {str(d["discussion_id"]) for d in tree["discussions"]}
    assert str(tree["current_discussion_id"]) in discussion_ids
