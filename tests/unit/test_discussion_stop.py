from threading import Event
from types import SimpleNamespace
from unittest.mock import patch


def test_stop_prompt_sets_event_and_returns_discussion_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    import importlib

    discussions = importlib.import_module("src.lib.discussions")
    importlib.reload(discussions)

    state = discussions.DiscussionState()
    created = state._create_discussion(owner_user_id=1, title="Test")
    discussion_id = created["discussion_id"]
    state._set_current_discussion(1, discussion_id)
    state._streaming.add(discussion_id)
    stop_event = Event()
    state._stop_events[discussion_id] = stop_event

    result = state.stop_prompt(user_id=1, member_group_ids=set())

    assert result == discussion_id
    assert stop_event.is_set()


@patch("src.lib.discussions.prompt_llm.execute")
@patch("src.lib.discussions.prompt_llm.TextFileStorage")
@patch("src.lib.discussions.prompt_llm.KoboldCppBackend")
def test_prompt_llm_passes_stop_event(mock_backend_class, mock_storage_class, mock_execute, tmp_path):
    from src.lib.discussions.prompt_llm import prompt_llm

    output_file = tmp_path / "output.txt"
    output_file.write_text("done", encoding="utf-8")
    mock_execute.return_value = SimpleNamespace(output_path=str(output_file))

    stop_event = Event()
    prompt_llm("Nick test", output_dir="/tmp/apmatia_logs", stop_event=stop_event)

    request = mock_execute.call_args.args[0]
    assert request.stop_event is stop_event


@patch("src.lib.discussions.prompt_llm.execute")
@patch("src.lib.discussions.prompt_llm.TextFileStorage")
@patch("src.lib.discussions.prompt_llm.KoboldCppBackend")
def test_prompt_llm_streams_chunks_to_callback(mock_backend_class, mock_storage_class, mock_execute, tmp_path):
    from src.lib.discussions.prompt_llm import prompt_llm

    output_file = tmp_path / "output.txt"
    output_file.write_text("Hello there", encoding="utf-8")

    def fake_execute(request, backend, storage):
        storage.initialize(request)
        storage.append(request, "Hello ")
        storage.append(request, "there")
        storage.finalize(request)
        return SimpleNamespace(output_path=str(output_file))

    mock_execute.side_effect = fake_execute
    streamed_chunks = []

    result = prompt_llm(
        "Nick test",
        output_dir=str(tmp_path),
        on_chunk=streamed_chunks.append,
    )

    assert result == "Hello there"
    assert streamed_chunks == ["Hello ", "there"]
