from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.api.internal.prompt_LLM import prompt_llm
from src.core.app_config import get_config_value, set_config_value
from src.core.discussions import discussion_state

router = APIRouter()


class PromptPayload(BaseModel):
    prompt: str


class SystemPromptPayload(BaseModel):
    system_prompt: str


class SettingsPayload(BaseModel):
    model_url: str
    max_response_size: int
    system_prompt: str
    theme: str = "dark"
    font_family: str = "system-ui"
    font_size: int = 16


@router.get("/prompt")
def prompt(prompt: str = "Hello", output_dir: str | None = None):
    return {"message": prompt_llm(prompt, output_dir=output_dir)}


@router.get("/discussion/state")
def discussion_snapshot():
    snapshot = discussion_state.snapshot()
    return {
        "discussion_id": snapshot.discussion_id,
        "is_streaming": snapshot.is_streaming,
        "last_error": snapshot.last_error,
        "system_prompt": snapshot.system_prompt,
        "content": snapshot.content,
    }


@router.post("/discussion/prompt")
def discussion_prompt(payload: PromptPayload):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    try:
        discussion_id = discussion_state.start_prompt(prompt)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "started", "discussion_id": discussion_id}


@router.post("/discussion/reset")
def reset_discussion():
    try:
        discussion_id = discussion_state.reset_discussion()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "reset", "discussion_id": discussion_id}


@router.post("/discussion/system_prompt")
def set_system_prompt(payload: SystemPromptPayload):
    discussion_state.set_system_prompt(payload.system_prompt)
    return {"status": "saved"}


@router.get("/settings")
def get_settings():
    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        model_url = get_config_value("llm", "koboldcpp", "base_url", default=None)
    else:
        model_url = get_config_value(
            "llm", "openai_compatible", "base_url", default=None
        )

    max_tokens = get_config_value("llm", "max_tokens", default=8192)
    system_prompt = get_config_value("discussion", "system_prompt", default="")
    theme = get_config_value("ui", "theme", default="dark")
    font_family = get_config_value("ui", "font_family", default="system-ui")
    font_size = get_config_value("ui", "font_size", default=16)
    return {
        "backend": backend_name,
        "model_url": str(model_url or ""),
        "max_response_size": int(max_tokens),
        "system_prompt": str(system_prompt or ""),
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "font_size": int(font_size),
    }


@router.post("/settings")
def save_settings(payload: SettingsPayload):
    model_url = payload.model_url.strip()
    system_prompt = payload.system_prompt

    if not model_url:
        raise HTTPException(status_code=400, detail="Model URL cannot be empty.")
    if payload.max_response_size < 1:
        raise HTTPException(
            status_code=400, detail="Max response size must be at least 1."
        )
    if payload.theme not in {"dark", "light"}:
        raise HTTPException(status_code=400, detail="Theme must be 'dark' or 'light'.")
    if payload.font_size < 12 or payload.font_size > 24:
        raise HTTPException(
            status_code=400, detail="Font size must be between 12 and 24."
        )

    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        set_config_value("llm", "koboldcpp", "base_url", value=model_url)
    else:
        set_config_value("llm", "openai_compatible", "base_url", value=model_url)

    set_config_value("llm", "max_tokens", value=payload.max_response_size)
    discussion_state.set_system_prompt(system_prompt)
    set_config_value("ui", "theme", value=payload.theme)
    set_config_value("ui", "font_family", value=payload.font_family)
    set_config_value("ui", "font_size", value=payload.font_size)
    return {"status": "saved"}
