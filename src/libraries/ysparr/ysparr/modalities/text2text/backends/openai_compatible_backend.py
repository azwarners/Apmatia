from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

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

        if isinstance(chat_messages, list):
            endpoint = "/v1/chat/completions"
            payload = self._build_chat_payload(request, chat_messages)
        else:
            endpoint = "/v1/completions"
            payload = self._build_completion_payload(request)

        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers()

        try:
            with requests.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    text = self._extract_text(line)
                    if text:
                        yield text
        except requests.RequestException as error:
            raise ExecutionError(
                f"OpenAI-compatible request failed: {error}"
            ) from error

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

    def _extract_text(self, line: str) -> str:
        payload = line.removeprefix("data:").strip()
        if not payload or payload == "[DONE]":
            return ""

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return ""

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
