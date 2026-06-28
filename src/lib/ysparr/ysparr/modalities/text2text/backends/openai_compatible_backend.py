from __future__ import annotations

import json
import os
import re
from ipaddress import ip_address
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse, urlunparse

import requests

from ysparr.core.config import get_config_value
from ysparr.core.exceptions import ExecutionError
from ysparr.core.types import PromptRequest


class OpenAICompatibleBackend:
    """
    Backend adapter for OpenAI-compatible APIs.

    Supports:
    - /v1/chat/completions (preferred when chat_messages are provided)
    - /v1/completions (prompt fallback)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.base_url = (
            base_url
            or get_config_value("text2text", "openai_compatible", "base_url")
        )
        if not self.base_url:
            raise ExecutionError(
                "OpenAI-compatible base_url not provided and not found in config"
            )
        self.base_url = self.base_url.rstrip("/")
        self.base_url = _resolve_docker_host_loopback(self.base_url)

        self.api_key = (
            api_key
            if api_key is not None
            else get_config_value("text2text", "openai_compatible", "api_key")
        )
        self.default_model_name = (
            model_name
            or get_config_value("text2text", "openai_compatible", "model_name")
            or "gpt-4o-mini"
        )
        self.timeout_seconds = timeout_seconds

    def stream(self, request: PromptRequest) -> Iterable[str]:
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        chat_messages = metadata.get("chat_messages")
        supports_multimodal = _contains_multimodal_messages(chat_messages)

        if isinstance(chat_messages, list):
            try:
                yield from self._stream_request(
                    request=request,
                    endpoint="/v1/chat/completions",
                    payload=self._build_chat_payload(request, chat_messages),
                )
                return
            except ExecutionError as error:
                if supports_multimodal or not _should_fallback_to_completion(error):
                    raise
            yield from self._stream_request(
                request=request,
                endpoint="/v1/completions",
                payload=self._build_completion_payload(request),
            )
            return
        else:
            yield from self._stream_request(
                request=request,
                endpoint="/v1/completions",
                payload=self._build_completion_payload(request),
            )
            return

    def _stream_request(self, *, request: PromptRequest, endpoint: str, payload: Dict[str, Any]) -> Iterable[str]:
        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers()
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        on_event = metadata.get("on_event")

        try:
            with requests.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                response.encoding = "utf-8"
                for line in response.iter_lines(decode_unicode=False):
                    if request.stop_event is not None and request.stop_event.is_set():
                        response.close()
                        break
                    if not line:
                        continue
                    data = self._decode_event(line)
                    if data is None:
                        continue
                    text = self._extract_text(data)
                    if text:
                        yield text
                    if callable(on_event):
                        on_event(
                            {
                                "provider": "openai_compatible",
                                "endpoint": endpoint,
                                "raw": data,
                                "text": text,
                                "stats": data.get("usage") if isinstance(data.get("usage"), dict) else {},
                            }
                        )
        except requests.RequestException as error:
            raise ExecutionError(
                f"OpenAI-compatible request failed: {error}"
            ) from error

    def stop(self, prompt_id: str) -> None:
        return None

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _resolve_model_name(self, request: PromptRequest) -> str:
        if request.model_name and request.model_name != "default":
            return request.model_name
        return self.default_model_name

    def _build_chat_payload(
        self, request: PromptRequest, chat_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self._resolve_model_name(request),
            "messages": chat_messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 8192,
        }
        payload.update(
            self._coerce_generation_params(request.parameters)
        )
        return payload

    def _build_completion_payload(self, request: PromptRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self._resolve_model_name(request),
            "prompt": request.prompt_text,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 8192,
        }
        payload.update(
            self._coerce_generation_params(request.parameters)
        )
        return payload

    def _coerce_generation_params(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(parameters, dict):
            return {}

        allowed_keys = {
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "seed",
        }
        return {k: v for k, v in parameters.items() if k in allowed_keys}

    def _decode_event(self, line: bytes | str) -> dict[str, Any] | None:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        payload = line.removeprefix("data:").strip()
        if not payload or payload == "[DONE]":
            return None

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        return data

    def _extract_text(self, data: dict[str, Any]) -> str:
        if not isinstance(data, dict):
            return ""

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""

        # Chat Completions streaming shape.
        delta = first_choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content

        # Completions streaming shape.
        text = first_choice.get("text")
        if isinstance(text, str):
            return text

        # Some compatible providers send message.content.
        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content

        return ""


def _should_fallback_to_completion(error: ExecutionError) -> bool:
    message = str(error)
    return bool(
        re.search(r"\b(400|404)\b", message)
        or "chat/completions" in message
        or "not found" in message.lower()
        or "bad request" in message.lower()
    )


def _contains_multimodal_messages(chat_messages: Any) -> bool:
    if not isinstance(chat_messages, list):
        return False
    for message in chat_messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                return True
    return False


def _resolve_docker_host_loopback(base_url: str) -> str:
    """Route localhost targets to the host gateway when running inside Docker."""
    if not _running_in_docker():
        return base_url

    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if hostname is None:
        return base_url

    try:
        if not ip_address(hostname).is_loopback and hostname != "localhost":
            return base_url
    except ValueError:
        if hostname != "localhost":
            return base_url

    gateway_host = _docker_gateway_host() or "host.docker.internal"
    netloc = gateway_host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        netloc = f"{auth}@{netloc}"

    return urlunparse(parsed._replace(netloc=netloc))


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("APMATIA_IN_DOCKER") == "1"


def _docker_gateway_host() -> str | None:
    """Return the host-side gateway IP for the default Docker route, if available."""
    try:
        with open("/proc/net/route", encoding="utf-8") as route_file:
            for line in route_file.readlines()[1:]:
                parts = line.split()
                if len(parts) < 3:
                    continue
                destination = parts[1]
                gateway_hex = parts[2]
                flags_hex = parts[3] if len(parts) > 3 else "0"
                if destination != "00000000":
                    continue
                if int(flags_hex, 16) & 2 == 0:
                    continue
                gateway_bytes = bytes.fromhex(gateway_hex)
                return ".".join(str(byte) for byte in gateway_bytes[::-1])
    except (OSError, ValueError):
        return None
    return None
