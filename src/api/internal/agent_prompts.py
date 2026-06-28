from dataclasses import asdict

from src.core.agent_management_runtime import get_agent_manager


def create_agent_prompt(**kwargs) -> dict:
    manager = get_agent_manager()
    prompt, prompt_id = manager.create_prompt(**kwargs)
    return {"id": prompt_id, **asdict(prompt)}


def get_agent_prompt(prompt_id: int) -> dict | None:
    manager = get_agent_manager()
    prompt = manager.get_prompt(prompt_id)
    if prompt is None:
        return None
    return {"id": prompt_id, **asdict(prompt)}


def update_agent_prompt(prompt_id: int, **updates) -> dict:
    manager = get_agent_manager()
    prompt = manager.update_prompt(prompt_id, **updates)
    return {"id": prompt_id, **asdict(prompt)}


def compile_agent_prompt(name: str, **kwargs) -> str:
    manager = get_agent_manager()
    from src.lib.agent_management.agent_prompt import AgentPrompt

    return manager.compile_agent_system_prompt(name, AgentPrompt(**kwargs))


def get_agent_system_prompt(agent_id: int) -> str:
    manager = get_agent_manager()
    return manager.get_agent_system_prompt(agent_id)


def get_compiled_agent_prompt(prompt_id: int, name: str | None = None) -> str:
    manager = get_agent_manager()
    prompt = manager.get_prompt(prompt_id)
    if prompt is None:
        raise ValueError(f"Agent prompt not found: {prompt_id}")
    return manager.compile_agent_system_prompt(name or "Agent", prompt)
