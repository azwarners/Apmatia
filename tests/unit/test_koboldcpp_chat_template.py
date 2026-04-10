import pytest

from ysparr.core.exceptions import ExecutionError
from ysparr.core.types import PromptRequest
from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend


class FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=True):
        for line in self._lines:
            yield line

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_stream_uses_rendered_chat_template(monkeypatch):
    captured_payload = {}

    def fake_post(url, json=None, stream=None):
        captured_payload.update(json or {})
        return FakeResponse(["ok"])

    monkeypatch.setattr("requests.post", fake_post)

    backend = KoboldCppBackend(base_url="http://fake")
    request = PromptRequest(
        prompt_id="test",
        prompt_text="fallback prompt",
        model_name="test",
        metadata={
            "chat_template": "{% for m in messages %}{{ m.role }}: {{ m.content }}\\n{% endfor %}{% if add_generation_prompt %}assistant:{% endif %}",
            "chat_messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Say hi"},
            ],
            "add_generation_prompt": True,
        },
    )

    chunks = list(backend.stream(request))

    assert chunks == ["ok"]
    assert captured_payload["prompt"].strip().endswith("assistant:")
    assert "system: You are helpful." in captured_payload["prompt"]
    assert "user: Say hi" in captured_payload["prompt"]


def test_stream_falls_back_to_prompt_text_without_template(monkeypatch):
    captured_payload = {}

    def fake_post(url, json=None, stream=None):
        captured_payload.update(json or {})
        return FakeResponse(["ok"])

    monkeypatch.setattr("requests.post", fake_post)

    backend = KoboldCppBackend(base_url="http://fake")
    request = PromptRequest(
        prompt_id="test",
        prompt_text="plain prompt",
        model_name="test",
    )

    list(backend.stream(request))

    assert captured_payload["prompt"] == "plain prompt"


def test_stream_raises_for_invalid_chat_template(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(["ok"])

    monkeypatch.setattr("requests.post", fake_post)

    backend = KoboldCppBackend(base_url="http://fake")
    request = PromptRequest(
        prompt_id="test",
        prompt_text="plain prompt",
        model_name="test",
        metadata={
            "chat_template": "{{ missing_var }}",
            "chat_messages": [{"role": "user", "content": "hi"}],
        },
    )

    with pytest.raises(ExecutionError):
        list(backend.stream(request))
