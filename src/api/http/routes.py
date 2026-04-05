from fastapi import APIRouter
from src.api.internal.prompt_LLM import prompt_llm

router = APIRouter()

@router.get("/prompt")
def prompt(prompt: str = "Hello"):
    return {"message": prompt_llm(prompt)}
