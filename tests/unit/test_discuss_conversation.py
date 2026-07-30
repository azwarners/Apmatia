from types import SimpleNamespace
from unittest.mock import patch

from apmatia.modules.discuss.services import prompt_llm


def _execute_result(tmp_path):
    output_path = tmp_path / "response.txt"
    output_path.write_text('{"results": [{"text": "ok"}]}', encoding="utf-8")
    return SimpleNamespace(output_path=str(output_path))


def test_direct_prompt_does_not_inject_role_labels(tmp_path):
    captured = {}

    def execute(request, backend, storage):
        captured["prompt_text"] = request.prompt_text
        return _execute_result(tmp_path)

    with patch("apmatia.modules.discuss.services.execute", side_effect=execute), patch(
        "apmatia.modules.discuss.services.OpenAICompatibleBackend"
    ):
        result = prompt_llm("Plan the homepage", output_dir=str(tmp_path))

    assert result == "ok"
    assert captured["prompt_text"] == "Plan the homepage"
    assert "User:" not in captured["prompt_text"]
    assert "Assistant:" not in captured["prompt_text"]


def test_group_prompt_uses_named_user_and_speaker_labels(tmp_path):
    captured = {}

    def execute(request, backend, storage):
        captured["prompt_text"] = request.prompt_text
        return _execute_result(tmp_path)

    with patch("apmatia.modules.discuss.services.execute", side_effect=execute), patch(
        "apmatia.modules.discuss.services.OpenAICompatibleBackend"
    ):
        prompt_llm(
            "Review the proposal",
            context="Nick: Start planning\nAda the Architect: I suggest a component layout.",
            request_metadata={
                "conversation_mode": "group",
                "user_name": "Nick",
                "speaker_name": "Beatrice the Coder",
            },
            output_dir=str(tmp_path),
        )

    assert captured["prompt_text"] == (
        "Nick: Start planning\n"
        "Ada the Architect: I suggest a component layout.\n"
        "Nick: Review the proposal\n"
        "Beatrice the Coder:"
    )
    assert "User:" not in captured["prompt_text"]
    assert "Assistant:" not in captured["prompt_text"]
