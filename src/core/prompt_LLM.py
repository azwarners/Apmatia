import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from src.core.app_config import get_config_value

try:
    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        OpenAICompatibleBackend,
    )
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    ysparr_src = repo_root / "src" / "lib" / "ysparr"
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
) -> str:
    if context and context.strip():
        prompt_text = f"{context.rstrip()}\nUser: {prompt}\nAssistant:"
    else:
        prompt_text = f"User: {prompt}\nAssistant:"

    model_name = (
        get_config_value("llm", "model_name", default=None)
        or os.getenv("LLM_MODEL")
        or "default"
    )
    request = PromptRequest(
        prompt_id=prompt_id or str(uuid.uuid4()),
        prompt_text=prompt_text,
        model_name=model_name,
        parameters=_default_generation_parameters(),
        metadata={
            "append_existing": append_existing,
            **(request_metadata or {}),
        },
    )

    backend = _build_backend()
    apmatia_home = Path(
        os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))
    ).expanduser()
    resolved_output_dir = (
        Path(output_dir).expanduser()
        if output_dir is not None
        else apmatia_home / "prompt_logs"
    )
    storage = TextFileStorage(str(resolved_output_dir))
    result = execute(request, backend, storage)

    raw_text = Path(result.output_path).read_text(encoding="utf-8").strip()

    if append_existing:
        return raw_text

    try:
        payload = json.loads(raw_text)
        return payload["results"][0]["text"].strip()
    except Exception:
        return raw_text


def _build_backend():
    backend_name = (
        get_config_value("llm", "backend", default=None)
        or os.getenv("YSPARR_TEXT2TEXT_BACKEND")
        or "openai_compatible"
    ).strip().lower()

    if backend_name in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleBackend(
            base_url=(
                get_config_value("llm", "openai_compatible", "base_url", default=None)
                or os.getenv("OPENAI_COMPAT_BASE_URL")
            ),
            api_key=(
                get_config_value("llm", "openai_compatible", "api_key", default=None)
                or os.getenv("OPENAI_COMPAT_API_KEY")
            ),
            model_name=(
                get_config_value("llm", "openai_compatible", "model_name", default=None)
                or os.getenv("OPENAI_COMPAT_MODEL")
            ),
        )

    return KoboldCppBackend(
        base_url=(
            get_config_value("llm", "koboldcpp", "base_url", default=None)
            or os.getenv("KOBOLDCPP_URL")
            or "http://localhost:5001"
        )
    )


def _default_generation_parameters() -> dict[str, Any]:
    max_tokens_value = (
        get_config_value("llm", "max_tokens", default=None)
        or os.getenv("LLM_MAX_TOKENS")
        or 8192
    )
    max_tokens = int(max_tokens_value)
    return {"max_tokens": max_tokens}
