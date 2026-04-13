from fastapi import APIRouter
from src.api.internal.prompt_LLM import prompt_llm

from .shared import require_session

router = APIRouter()


@router.get("/prompt")
def prompt(request, prompt: str = "Hello", output_dir: str | None = None):
    require_session(request)
    return {"message": prompt_llm(prompt, output_dir=output_dir)}
