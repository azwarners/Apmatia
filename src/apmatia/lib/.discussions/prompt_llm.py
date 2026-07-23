import json
import os
import sys
import uuid
from threading import Event
from pathlib import Path
from typing import Any, Callable

from apmatia.core.app_config import get_config_value
from apmatia.modules.ai_model_manager.models import LLMConfig as LLM

try:
    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        OpenAICompatibleBackend,
    )
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[4]
    ysparr_src = repo_root / "src" / "apmatia" / "lib" / "ysparr"
    if str(ysparr_src) not in sys.path:
        sys.path.append(str(ysparr_src))

    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        OpenAICompatibleBackend,
    )
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage


def prompt_llm(
    prompt: str = "Hello",
    output_dir: str | None = None,
    prompt_id: str | None = None,
    append_existing: bool = False,
    context: str | None = None,
    request_metadata: dict[str, Any] | None = None,
    llm_config: LLM | None = None,
    stop_event: Event | None = None,
    on_chunk: Callable[[str], None] | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    if context and context.strip():
        prompt_text = f"{context.rstrip()}\nUser: {prompt}\nAssistant:"
    else:
        prompt_text = f"User: {prompt}\nAssistant:"

    model_name = _resolve_model_name(llm_config)
    request = PromptRequest(
        prompt_id=prompt_id or str(uuid.uuid4()),
        prompt_text=prompt_text,
        model_name=model_name,
        parameters=_default_generation_parameters(llm_config),
        metadata={
            "append_existing": append_existing,
            **(request_metadata or {}),
            "on_event": on_event,
        },
        stop_event=stop_event,
    )

    backend = _build_backend(llm_config)
    apmatia_home = Path(
        os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))
    ).expanduser()
    resolved_output_dir = (
        Path(output_dir).expanduser()
        if output_dir is not None
        else apmatia_home / "prompt_logs"
    )
    if on_chunk is None:
        storage = TextFileStorage(str(resolved_output_dir))
    else:
        storage = _ChunkCallbackStorage(str(resolved_output_dir), on_chunk=on_chunk)
    result = execute(request, backend, storage)

    raw_text = Path(result.output_path).read_text(encoding="utf-8").strip()

    if append_existing:
        return raw_text

    try:
        payload = json.loads(raw_text)
        return payload["results"][0]["text"].strip()
    except Exception:
        return raw_text


def _resolve_model_name(llm_config: LLM | None) -> str:
    if llm_config is not None:
        provider_name = str(getattr(llm_config, "provider_name", "") or "").strip()
        if not provider_name:
            provider_name = str(getattr(llm_config, "provider_model_name", "") or "").strip()
        if provider_name:
            return provider_name
        model_name = str(getattr(llm_config, "user_alias", "") or "").strip()
        if not model_name:
            model_name = str(getattr(llm_config, "model_name", "") or "").strip()
        if model_name:
            return model_name
    model_name = (
        get_config_value("llm", "model_name", default=None)
        or os.getenv("LLM_MODEL")
        or "default"
    )
    return str(model_name)


def _build_backend(llm_config: LLM | None = None):
    backend_name = (
        (llm_config.backend if llm_config is not None else None)
        or get_config_value("llm", "backend", default=None)
        or os.getenv("YSPARR_TEXT2TEXT_BACKEND")
        or "openai_compatible"
    ).strip().lower()

    if backend_name in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleBackend(
            base_url=(
                (llm_config.model_url if llm_config is not None else None)
                or get_config_value("llm", "openai_compatible", "base_url", default=None)
                or os.getenv("OPENAI_COMPAT_BASE_URL")
            ),
            api_key=(
                (llm_config.api_key if llm_config is not None else None)
                or get_config_value("llm", "openai_compatible", "api_key", default=None)
                or os.getenv("OPENAI_COMPAT_API_KEY")
            ),
            model_name=(
                _resolve_model_name(llm_config)
                or get_config_value("llm", "openai_compatible", "model_name", default=None)
                or os.getenv("OPENAI_COMPAT_MODEL")
            ),
            timeout_seconds=None,
        )

    return KoboldCppBackend(
        base_url=(
            (llm_config.model_url if llm_config is not None else None)
            or get_config_value("llm", "koboldcpp", "base_url", default=None)
            or os.getenv("KOBOLDCPP_URL")
            or "http://localhost:5001"
        )
    )


def _default_generation_parameters(llm_config: LLM | None = None) -> dict[str, Any]:
    max_tokens_value = (
        (llm_config.max_response_size if llm_config is not None else None)
        or get_config_value("llm", "max_tokens", default=None)
        or os.getenv("LLM_MAX_TOKENS")
        or 8192
    )
    max_tokens = int(max_tokens_value)
    return {"max_tokens": max_tokens}


class _ChunkCallbackStorage(TextFileStorage):
    def __init__(self, output_dir: str, *, on_chunk: Callable[[str], None] | None = None) -> None:
        super().__init__(output_dir)
        self._on_chunk = on_chunk

    def append(self, request: PromptRequest, text: str) -> None:
        super().append(request, text)
        if self._on_chunk is not None and text:
            self._on_chunk(text)
