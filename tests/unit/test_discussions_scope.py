import importlib


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
