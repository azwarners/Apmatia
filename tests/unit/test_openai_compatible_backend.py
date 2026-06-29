from unittest.mock import patch
from unittest.mock import mock_open

import requests

from ysparr.core.types import PromptRequest
from ysparr.modalities.text2text.backends.openai_compatible_backend import (
    OpenAICompatibleBackend,
    _docker_gateway_host,
    _resolve_docker_host_loopback,
)


def test_resolve_docker_host_loopback_leaves_non_loopback_urls_unchanged():
    with patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker",
        return_value=True,
    ):
        assert (
            _resolve_docker_host_loopback("http://example.local:8080")
            == "http://example.local:8080"
        )


def test_resolve_docker_host_loopback_rewrites_localhost_in_docker():
    with patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker",
        return_value=True,
    ), patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._docker_gateway_host",
        return_value="172.17.0.1",
    ):
        assert (
            _resolve_docker_host_loopback("http://127.0.0.1:8080")
            == "http://172.17.0.1:8080"
        )


def test_docker_gateway_host_reads_default_route():
    route_data = """Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT
eth0\t00000000\t010012AC\t0003\t0\t0\t0\t00000000\t0\t0\t0
"""

    with patch("builtins.open", mock_open(read_data=route_data)):
        assert _docker_gateway_host() == "172.18.0.1"


def test_backend_uses_host_gateway_for_loopback_urls_in_docker(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        captured["url"] = url

        class Response:
            def raise_for_status(self):
                pass

            encoding = None

            def iter_lines(self, decode_unicode=True):
                assert decode_unicode is False
                yield b"data: [DONE]"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return Response()

    monkeypatch.setattr("requests.post", fake_post)

    with patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker",
        return_value=True,
    ), patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._docker_gateway_host",
        return_value="172.18.0.1",
    ):
        backend = OpenAICompatibleBackend(base_url="http://127.0.0.1:8080")

    list(
        backend.stream(
            PromptRequest(prompt_id="test", prompt_text="hello", model_name="demo")
        )
    )

    assert captured["url"] == "http://172.18.0.1:8080/v1/completions"


def test_backend_falls_back_to_completions_when_chat_endpoint_rejects_request(monkeypatch):
    captured = []

    class FakeResponse:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            if self.url.endswith("/v1/chat/completions"):
                raise requests.HTTPError("400 Client Error: Bad Request for url: http://127.0.0.1:8080/v1/chat/completions")

        encoding = None

        def iter_lines(self, decode_unicode=True):
            assert decode_unicode is False
            yield b"data: {\"choices\":[{\"text\":\"fallback ok\"}]}"
            yield b"data: [DONE]"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        captured.append(url)
        return FakeResponse(url)

    monkeypatch.setattr("requests.post", fake_post)

    with patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker",
        return_value=False,
    ):
        backend = OpenAICompatibleBackend(base_url="http://127.0.0.1:8080")

    result = list(
        backend.stream(
            PromptRequest(
                prompt_id="test",
                prompt_text="hello",
                model_name="demo",
                metadata={"chat_messages": [{"role": "user", "content": "hello"}]},
            )
        )
    )

    assert captured == [
        "http://127.0.0.1:8080/v1/chat/completions",
        "http://127.0.0.1:8080/v1/completions",
    ]
    assert result == ["fallback ok"]


def test_backend_sends_multimodal_chat_messages(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        encoding = None

        def iter_lines(self, decode_unicode=True):
            assert decode_unicode is False
            yield b'data: {"choices":[{"delta":{"content":"vision ok"}}]}'
            yield b"data: [DONE]"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)

    with patch(
        "ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker",
        return_value=False,
    ):
        backend = OpenAICompatibleBackend(base_url="http://127.0.0.1:8080")

    result = list(
        backend.stream(
            PromptRequest(
                prompt_id="test",
                prompt_text="inspect the screenshot",
                model_name="demo",
                metadata={
                    "chat_messages": [
                        {"role": "system", "content": "You are helpful."},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "inspect the screenshot"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "data:image/png;base64,Zm9v"},
                                },
                            ],
                        },
                    ]
                },
            )
        )
    )

    assert captured["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert captured["json"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert result == ["vision ok"]
