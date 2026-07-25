import json

import requests

from apmatia.modules.ysparr.core.config import get_config_value
from apmatia.modules.ysparr.core.exceptions import ExecutionError
from apmatia.modules.ysparr.core.types import PromptRequest
from apmatia.modules.ysparr.modalities.text2text.templates import render_chat_template


class KoboldCppBackend:
    """
    Backend adapter for KoboldCpp.
    """

    def __init__(self, base_url: str | None = None):
        """
        Args:
            base_url: Optional override
        """

        self.base_url = (
            base_url
            or get_config_value("text2text", "koboldcpp", "base_url")
        )

        if not self.base_url:
            raise ExecutionError(
                "KoboldCpp base_url not provided and not found in config"
            )

        self.base_url = self.base_url.rstrip("/")

    def stream(self, request: PromptRequest):
        url = f"{self.base_url}/api/v1/generate"
        prompt_text = self._resolve_prompt_text(request)
        parameters = request.parameters if isinstance(request.parameters, dict) else {}
        max_tokens = int(parameters.get("max_tokens", 8192))
        temperature = float(parameters.get("temperature", 0.7))
        stop = parameters.get("stop", ["\nUser:"])
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        on_event = metadata.get("on_event")

        payload = {
            "prompt": prompt_text,
            "max_length": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stop": stop if isinstance(stop, list) else ["\nUser:"],
        }

        try:
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()
                response.encoding = "utf-8"

                for line in response.iter_lines(decode_unicode=False):
                    if request.stop_event is not None and request.stop_event.is_set():
                        response.close()
                        break
                    if not line:
                        continue

                    data = self._decode_event(line)
                    text = self._extract_text(line)
                    if text:
                        yield text
                    if callable(on_event):
                        on_event(
                            {
                                "provider": "koboldcpp",
                                "raw": data if data is not None else {"line": line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line},
                                "text": text,
                                "stats": data if isinstance(data, dict) else {},
                            }
                        )

        except requests.RequestException as error:
            raise ExecutionError("KoboldCpp request failed") from error

    def stop(self, prompt_id: str) -> None:
        url = f"{self.base_url}/api/extra/abort"
        try:
            requests.post(url, json={"id": prompt_id}, timeout=5)
        except requests.RequestException as error:
            raise ExecutionError("KoboldCpp stop request failed") from error

    def _resolve_prompt_text(self, request: PromptRequest) -> str:
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        template_text = metadata.get("chat_template")
        messages = metadata.get("chat_messages")

        if template_text is None or messages is None:
            return request.prompt_text

        add_generation_prompt = metadata.get("add_generation_prompt", True)
        extra_context = metadata.get("chat_template_context")
        return render_chat_template(
            template_text=template_text,
            messages=messages,
            add_generation_prompt=bool(add_generation_prompt),
            extra_context=extra_context if isinstance(extra_context, dict) else None,
        )

    def _extract_text(self, line: bytes | str) -> str:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        payload = line.removeprefix("data:").strip()
        if not payload:
            return ""

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return line

        if isinstance(data, dict):
            token = data.get("token")
            if isinstance(token, str):
                return token

            results = data.get("results")
            if (
                isinstance(results, list)
                and results
                and isinstance(results[0], dict)
                and isinstance(results[0].get("text"), str)
            ):
                return results[0]["text"]

            content = data.get("content")
            if isinstance(content, str):
                return content

        return ""

    def _decode_event(self, line: bytes | str) -> dict[str, object] | None:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        payload = line.removeprefix("data:").strip()
        if not payload:
            return None

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
