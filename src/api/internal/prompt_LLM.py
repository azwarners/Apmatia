from src.core.prompt_LLM import prompt_llm as core_prompt_llm

def prompt_llm(
    prompt: str = "Hello",
    output_dir: str | None = None,
    prompt_id: str | None = None,
    append_existing: bool = False,
) -> str:
    return core_prompt_llm(
        prompt,
        output_dir=output_dir,
        prompt_id=prompt_id,
        append_existing=append_existing,
    )
