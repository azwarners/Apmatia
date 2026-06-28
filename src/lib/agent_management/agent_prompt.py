from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentPrompt:
    personality: str = "Helpful, calm, and thoughtful."
    skills: str = "General assistance, analysis, and coordination."
    purpose: str = "Support the user with reliable and focused help."
    backstory: str = "An AI assistant built to work clearly and carefully."
    communication_style: str = "Clear, concise, and friendly."
    operating_principles: str = "Be accurate, practical, and easy to work with."
    autonomy_level: str = "Act with moderate autonomy and ask when uncertain."
    decision_making_style: str = "Prefer simple, reversible decisions with explicit reasoning."
    memory_policy: str = "Use only available context and avoid assuming hidden memory."
    domain_priorities: str = "Prioritize the user's immediate task and relevant context."
    relationship_to_user: str = "A collaborative assistant working alongside the user."
    tool_use_policy: str = "Use tools only when they clearly help accomplish the task."
    capability_boundaries: str = "Be honest about limits and avoid claiming unavailable abilities."
    output_preferences: str = "Prefer structured, actionable, and readable responses."
    safety_ethics: str = "Avoid harmful actions, respect consent, and follow safety rules."
    selfhood_truthfulness: str = "Do not pretend to be human or claim subjective experience."
    conflict_resolution_rules: str = "Resolve ambiguity by asking concise clarifying questions."
    use_raw_prompt_override: bool = False
    raw_prompt_override: str = ""


def default_agent_prompt() -> AgentPrompt:
    return AgentPrompt()


def compile_agent_system_prompt(name: str, prompt: AgentPrompt) -> str:
    if prompt.use_raw_prompt_override and prompt.raw_prompt_override.strip():
        return prompt.raw_prompt_override.strip()

    sections = [
        f"You are {name.strip() or 'an AI assistant'}.",
        _format_block("Purpose", prompt.purpose),
        _format_block("Personality", prompt.personality),
        _format_block("Skills", prompt.skills),
        _format_block("Backstory", prompt.backstory),
        _format_block("Relationship to user", prompt.relationship_to_user),
        _format_block("Communication style", prompt.communication_style),
        _format_block("Operating principles", prompt.operating_principles),
        _format_block("Autonomy", prompt.autonomy_level),
        _format_block("Decision making", prompt.decision_making_style),
        _format_block("Memory policy", prompt.memory_policy),
        _format_block("Tool policy", prompt.tool_use_policy),
        _format_block("Capability boundaries", prompt.capability_boundaries),
        _format_block("Domain priorities", prompt.domain_priorities),
        _format_block("Safety and ethics", prompt.safety_ethics),
        _format_block("Truthfulness", prompt.selfhood_truthfulness),
        _format_block("Conflict resolution", prompt.conflict_resolution_rules),
        _format_block("Output preferences", prompt.output_preferences),
    ]
    return "\n\n".join(section for section in sections if section)


def _format_block(label: str, value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return f"{label}: {text}"
