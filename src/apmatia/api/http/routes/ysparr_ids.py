"""Stable identifiers shared by the Apmatia-owned Ysparr extension."""


def legacy_agent_model_id(agent_id: int) -> str:
    return f"apmatia-agent-{agent_id}"


def named_agent_model_id(name: str) -> str:
    return name
