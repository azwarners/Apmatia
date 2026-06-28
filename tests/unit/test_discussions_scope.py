import importlib
import base64

import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from src.lib.agent_management.agent_prompt import AgentPrompt


def test_discussion_private_scope_is_per_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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
    discussions = importlib.import_module("src.lib.discussions")
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


def test_discussion_can_store_focused_wiki_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(
        owner_user_id=101,
        title="Tutor Thread",
        focused_wiki_id="wiki_focus01",
    )
    updated = state.update_discussion(
        owner_user_id=101,
        discussion_id=str(created["discussion_id"]),
        focused_wiki_id="wiki_focus02",
    )

    assert created["focused_wiki_id"] == "wiki_focus01"
    assert updated["focused_wiki_id"] == "wiki_focus02"


def test_discussion_can_persist_and_hydrate_prompt_attachments(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Screenshot Thread")
    discussion_id = str(created["discussion_id"])
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2W7p8AAAAASUVORK5CYII="
    )
    attachment_payload = {
        "filename": "screenshot.png",
        "mime_type": "image/png",
        "data_base64": base64.b64encode(png_bytes).decode("ascii"),
    }

    stored = state._store_prompt_attachments(discussion_id, [attachment_payload])
    assert stored[0]["mime_type"] == "image/png"
    assert stored[0]["path"].startswith("attachments/")

    hydrated = state._hydrate_message_attachments(
        discussion_id,
        {
            "role": "User",
            "text": "Please inspect this.",
            "metadata": {"attachments": stored},
        },
    )

    attachments = hydrated["metadata"]["attachments"]
    assert attachments[0]["data_url"].startswith("data:image/png;base64,")


def test_delete_discussion_moves_discussion_to_trash(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Old Thread")

    result = state.delete_discussion(
        owner_user_id=101,
        discussion_id=str(created["discussion_id"]),
    )

    assert result["discussion_id"] == created["discussion_id"]
    tree = state.list_tree(user_id=101, member_group_ids=set())
    assert created["discussion_id"] not in {
        discussion["discussion_id"] for discussion in tree["discussions"]
    }
    trash = state.list_trash(owner_user_id=101)
    assert created["discussion_id"] in {
        discussion["discussion_id"] for discussion in trash["discussions"]
    }


def test_delete_last_discussion_does_not_auto_create_replacement_in_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Only Thread")
    state.open_discussion(
        user_id=101,
        discussion_id=str(created["discussion_id"]),
        member_group_ids=set(),
    )

    deleted = state.delete_discussion(
        owner_user_id=101,
        discussion_id=str(created["discussion_id"]),
    )

    assert deleted["next_discussion_id"] is None
    tree = state.list_tree(user_id=101, member_group_ids=set())
    assert tree["current_discussion_id"] is None
    assert tree["discussions"] == []


def test_start_prompt_records_agent_participation(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Agent Thread")
    state.open_discussion(
        user_id=101,
        discussion_id=str(created["discussion_id"]),
        member_group_ids=set(),
    )
    monkeypatch.setattr(
        discussions.threading,
        "Thread",
        lambda target, args, daemon: SimpleNamespace(start=lambda: None),
    )

    state.start_prompt(
        user_id=101,
        prompt="Hello",
        member_group_ids=set(),
        agent_id=7,
    )

    updated = state._get_discussion(str(created["discussion_id"]))
    assert updated is not None
    assert updated.participant_agent_ids == [7]


def test_round_robin_group_chat_streams_named_agent_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.side_effect = lambda agent_id: {
        7: SimpleNamespace(
            id=7,
            name="Alpha",
            prompt_id=None,
            active_model_id=1,
            default_model_id=1,
        ),
        8: SimpleNamespace(
            id=8,
            name="Beta",
            prompt_id=None,
            active_model_id=1,
            default_model_id=1,
        ),
    }.get(agent_id)
    llm_manager = Mock()
    llm_manager.list_configs.return_value = [SimpleNamespace(id=1, backend="openai_compatible", model_name="group")]
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    tool_manager = Mock()
    tool_manager.list_tools_available_to_agent.return_value = []
    monkeypatch.setattr(discussions, "get_tool_manager", lambda: tool_manager)

    replies = ["Alpha reply", "Beta reply"]

    def fake_prompt_llm(**kwargs):
        return replies.pop(0)

    monkeypatch.setattr(discussions, "prompt_llm", fake_prompt_llm)

    state = discussions.DiscussionState()
    created = state.create_discussion(
        owner_user_id=101,
        title="Group Chat",
        participant_agent_ids=[7, 8],
        chat_mode="round_robin",
    )

    state._run_prompt(created["discussion_id"], "Hello group", agent_id=7)

    transcript = state._discussion_path(created["discussion_id"]).read_text(encoding="utf-8")
    assert "User: Hello group" in transcript
    assert "Agent (Alpha): Alpha reply" in transcript
    assert "Agent (Beta): Beta reply" in transcript


def test_discussion_object_id_matches_discussion_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Typed Thread")

    discussion = state._get_discussion(created["discussion_id"])

    assert discussion is not None
    assert discussion.id == created["discussion_id"]
    assert discussion.discussion_id == created["discussion_id"]


def test_discussion_transcript_preserves_message_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Metadata Thread")
    state.open_discussion(user_id=101, discussion_id=created["discussion_id"], member_group_ids=set())
    path = state._discussion_path(created["discussion_id"])
    path.write_text(
        state._format_messages(
            [
                {"role": "User", "text": "Hello"},
                {
                    "role": "Agent",
                    "speaker_name": "Alpha",
                    "text": "Reply",
                    "metadata": {
                        "llama_server_status": {
                            "generation": {"tokens_per_second": 22.6},
                            "total_tokens": 1559,
                        }
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    parsed = state._parse_messages(path.read_text(encoding="utf-8"))
    assert parsed[1]["metadata"]["llama_server_status"]["total_tokens"] == 1559


def test_discussion_snapshot_backfills_renderable_llama_status_when_metadata_is_unhelpful(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Metadata Thread")
    state.open_discussion(user_id=101, discussion_id=created["discussion_id"], member_group_ids=set())
    path = state._discussion_path(created["discussion_id"])
    path.write_text(
        state._format_messages(
            [
                {"role": "User", "text": "Hello"},
                {
                    "role": "Assistant",
                    "text": "Reply",
                    "metadata": {
                        "llama_server_status": {
                            "usage": {
                                "prompt_tokens": 10,
                                "completion_tokens": 5,
                                "total_tokens": 15,
                            }
                        }
                    },
                },
            ]
        ),
        encoding="utf-8",
    )
    state._llama_server_turns = lambda: [
        {
            "chat_format": "peg-native",
            "thinking_enabled": True,
            "selected_slot_id": 0,
            "current_task_id": 220,
            "prompt_processing_progress": 0.995794,
            "prompt_processing_n_tokens": 947,
            "prompt_tokens_total": 951,
            "prompt_eval": {"tokens_per_second": 203.64},
            "eval": {"tokens_per_second": 22.6},
            "total_time_ms": 31612.67,
            "total_tokens": 1559,
            "slots_idle": False,
        }
    ]

    snapshot = state.snapshot(user_id=101, member_group_ids=set())

    assert snapshot.messages[1]["metadata"]["llama_server_status"]["total_tokens"] == 1559
    assert "prompt_processing_progress" in snapshot.messages[1]["metadata"]["llama_server_status"]


def test_legacy_discussion_rows_missing_base_fields_still_load(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    state._ensure_store.insert(
        "discussions",
        {
            "discussion_id": "IDlegacy01",
            "title": "Legacy Thread",
            "owner_user_id": 101,
            "group_id": None,
            "system_prompt": "",
            "last_error": None,
            "deleted_at": None,
            "purge_after": None,
        },
    )

    discussion = state._get_discussion("IDlegacy01")

    assert discussion is not None
    assert discussion.id == "IDlegacy01"
    assert discussion.mode == 0
    assert discussion.owner_group_id is None
    assert discussion.created_at.tzinfo is not None
    assert discussion.updated_at.tzinfo is not None


def test_snapshot_includes_parsed_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
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


def test_snapshot_separates_streaming_assistant_turn_from_user_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    snapshot = state.snapshot(user_id=101, member_group_ids=set())
    transcript_path = state._discussion_path(snapshot.discussion_id)
    transcript_path.write_text(
        "User: Hello there\nAssistant: Hi! I am streaming\nmore text\n",
        encoding="utf-8",
    )

    updated_snapshot = state.snapshot(user_id=101, member_group_ids=set())
    assert updated_snapshot.messages == [
        {"role": "User", "text": "Hello there"},
        {"role": "Assistant", "text": "Hi! I am streaming\nmore text"},
    ]


def test_update_message_rewrites_discussion_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    snapshot = state.snapshot(user_id=101, member_group_ids=set())
    transcript_path = state._discussion_path(snapshot.discussion_id)
    transcript_path.write_text(
        "User: Hello there\n\nAssistant: Hi!\n",
        encoding="utf-8",
    )

    state.update_message(
        owner_user_id=101,
        discussion_id=snapshot.discussion_id,
        message_index=1,
        text="Hello again",
    )

    assert transcript_path.read_text(encoding="utf-8") == "User: Hello there\n\nAssistant: Hello again\n"


def test_delete_message_removes_selected_transcript_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    snapshot = state.snapshot(user_id=101, member_group_ids=set())
    transcript_path = state._discussion_path(snapshot.discussion_id)
    transcript_path.write_text(
        "User: Hello there\n\nAssistant: Hi!\n",
        encoding="utf-8",
    )

    state.delete_message(
        owner_user_id=101,
        discussion_id=snapshot.discussion_id,
        message_index=0,
    )

    assert transcript_path.read_text(encoding="utf-8") == "Assistant: Hi!\n"


def test_start_prompt_prefers_active_model_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.return_value = SimpleNamespace(active_model_id=12, default_model_id=34)
    llm_manager = Mock()
    llm_manager.list_configs.return_value = [
        SimpleNamespace(id=12, backend="openai_compatible", model_name="active"),
        SimpleNamespace(id=34, backend="openai_compatible", model_name="default"),
    ]
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    monkeypatch.setattr(discussions, "prompt_llm", lambda **kwargs: "agent reply")

    state = discussions.DiscussionState()
    resolved = state._resolve_agent_llm_config(7)

    assert resolved.id == 12


def test_start_prompt_falls_back_to_default_model_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.return_value = SimpleNamespace(active_model_id=None, default_model_id=34)
    llm_manager = Mock()
    llm_manager.list_configs.return_value = [SimpleNamespace(id=34, backend="koboldcpp", model_name="fallback")]
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    monkeypatch.setattr(discussions, "prompt_llm", lambda **kwargs: "agent reply")

    state = discussions.DiscussionState()
    resolved = state._resolve_agent_llm_config(7)

    assert resolved.id == 34


def test_start_prompt_errors_when_agent_has_no_model(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.return_value = SimpleNamespace(active_model_id=None, default_model_id=None)
    llm_manager = Mock()
    llm_manager.list_configs.return_value = []
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    monkeypatch.setattr(discussions, "prompt_llm", lambda **kwargs: "agent reply")

    state = discussions.DiscussionState()


def test_start_prompt_uses_agent_system_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.return_value = SimpleNamespace(
        active_model_id=12,
        default_model_id=34,
        prompt_id=99,
        name="Helper",
    )
    agent_manager.get_prompt.return_value = AgentPrompt(
        purpose="Help the user.",
        personality="Friendly.",
    )
    llm_manager = Mock()
    llm_manager.list_configs.return_value = [
        SimpleNamespace(id=12, backend="openai_compatible", model_name="active"),
    ]
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    tool_manager = Mock()
    tool_manager.list_tools_available_to_agent.return_value = [
        SimpleNamespace(
            id=1,
            name="echo",
            description="Return the provided text.",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        )
    ]
    monkeypatch.setattr(discussions, "get_tool_manager", lambda: tool_manager)
    wiki_manager = Mock()
    wiki_manager.get_wiki.return_value = SimpleNamespace(title="Tutor Wiki")
    monkeypatch.setattr(discussions, "get_wiki_manager", lambda: wiki_manager)

    captured = {}

    def fake_prompt_llm(**kwargs):
        captured.update(kwargs)
        return "agent reply"

    monkeypatch.setattr(discussions, "prompt_llm", fake_prompt_llm)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Prompt Test", focused_wiki_id="wiki-123")
    state._run_prompt(created["discussion_id"], "Hello", agent_id=7)

    assert captured["request_metadata"]["chat_messages"][0]["role"] == "system"
    assert "You are Helper." in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "Purpose: Help the user." in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "Current tutor session wiki:" in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "- wiki_title: Tutor Wiki" in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "Do not ask the user for a wiki ID" in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "Tool calling is available for this discussion." in captured["request_metadata"]["chat_messages"][0]["content"]
    assert "- echo: Return the provided text." in captured["request_metadata"]["chat_messages"][0]["content"]


def test_run_prompt_executes_tool_calls_and_stores_final_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    agent_manager = Mock()
    agent_manager.get_agent.return_value = SimpleNamespace(
        active_model_id=12,
        default_model_id=12,
        prompt_id=99,
        name="Helper",
    )
    agent_manager.get_prompt.return_value = AgentPrompt(
        purpose="Help the user.",
        personality="Friendly.",
    )
    llm_manager = Mock()
    llm_manager.list_configs.return_value = [
        SimpleNamespace(id=12, backend="openai_compatible", model_name="active"),
    ]
    tool_manager = Mock()
    tool_manager.list_tools_available_to_agent.return_value = [
        SimpleNamespace(
            id=1,
            name="echo",
            description="Return the provided text.",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        )
    ]
    tool_manager.execute_tool_call.return_value = SimpleNamespace(
        status="success",
        result={"text": "hello"},
        error=None,
    )
    monkeypatch.setattr(discussions, "get_agent_manager", lambda: agent_manager)
    monkeypatch.setattr(discussions, "get_llm_config_manager", lambda: llm_manager)
    monkeypatch.setattr(discussions, "get_tool_manager", lambda: tool_manager)

    calls = []

    def fake_prompt_llm(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            if kwargs.get("on_chunk") is not None:
                kwargs["on_chunk"]('<tool_call>{"name":"echo","arguments":{"text":"hello"}}</tool_call>')
            return '<tool_call>{"name":"echo","arguments":{"text":"hello"}}</tool_call>'
        if kwargs.get("on_chunk") is not None:
            kwargs["on_chunk"]("The tool ")
            kwargs["on_chunk"]("said hello.")
        return "The tool said hello."

    monkeypatch.setattr(discussions, "prompt_llm", fake_prompt_llm)

    state = discussions.DiscussionState()
    created = state.create_discussion(owner_user_id=101, title="Tool Prompt Test")
    state._run_prompt(created["discussion_id"], "Say hello", agent_id=7)

    transcript = state._discussion_path(created["discussion_id"]).read_text(encoding="utf-8")
    assert "User: Say hello" in transcript
    assert "Assistant: The tool said hello." in transcript
    assert "<tool_call>" not in transcript
    assert len(calls) == 2
    tool_manager.execute_tool_call.assert_called_once()
    second_messages = calls[1]["request_metadata"]["chat_messages"]
    assert second_messages[-1]["role"] == "user"
    assert '"tool": "echo"' in second_messages[-1]["content"]


def test_reset_discussion_carries_system_prompt_forward(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    state.set_system_prompt(user_id=101, member_group_ids=set(), system_prompt="be concise")

    new_discussion_id = state.reset_discussion(user_id=101)
    snapshot = state.snapshot(user_id=101, member_group_ids=set())

    assert snapshot.discussion_id == new_discussion_id
    assert snapshot.system_prompt == "be concise"


def test_list_tree_returns_empty_for_new_user_until_a_discussion_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))
    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    tree = state.list_tree(user_id=101, member_group_ids=set())

    assert tree["current_discussion_id"] is None
    assert tree["discussions"] == []
