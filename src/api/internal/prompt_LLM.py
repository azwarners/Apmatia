from src.core.prompt_LLM import prompt_llm as core_prompt_llm

def prompt_llm(prompt: str = "Hello") -> str:
    return core_prompt_llm(prompt)
