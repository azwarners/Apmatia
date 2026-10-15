"""Installer for the versioned, private-by-default starter agent catalog."""

from __future__ import annotations

from dataclasses import fields
from importlib.resources import files
import json
from typing import Any

from .agent_prompt import AgentPrompt
from .manager import DEFAULT_AGENT_MODE, AgentManager


_PROMPT_KEYS = {item.name for item in fields(AgentPrompt)}
_CATALOG_DIR = "starter_profiles"


def load_starter_profiles() -> list[dict[str, Any]]:
    """Load and validate the bundled profile data files."""
    profiles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for resource in sorted(files(__package__).joinpath(_CATALOG_DIR).iterdir(), key=lambda item: item.name):
        if resource.suffix != ".json":
            continue
        try:
            profile = json.loads(resource.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid starter profile file: {resource.name}") from error
        if not isinstance(profile, dict):
            raise ValueError(f"Starter profile must be an object: {resource.name}")
        profile_id = profile.get("profile_id")
        name = profile.get("name")
        specialization = profile.get("specialization")
        prompt = profile.get("prompt")
        if not all(isinstance(value, str) and value.strip() for value in (profile_id, name, specialization)):
            raise ValueError(f"Starter profile needs an ID, name, and specialization: {resource.name}")
        if profile_id in seen_ids:
            raise ValueError(f"Duplicate starter profile ID: {profile_id}")
        if not isinstance(prompt, dict) or not prompt:
            raise ValueError(f"Starter profile has no prompt fields: {resource.name}")
        unknown = set(prompt) - _PROMPT_KEYS
        if unknown:
            raise ValueError(f"Unsupported prompt fields in {resource.name}: {', '.join(sorted(unknown))}")
        missing = _PROMPT_KEYS - set(prompt)
        if missing:
            raise ValueError(f"Missing prompt fields in {resource.name}: {', '.join(sorted(missing))}")
        if prompt.get("use_raw_prompt_override") or prompt.get("raw_prompt_override"):
            raise ValueError(f"Starter profile cannot replace the compiled Apmatia prompt: {resource.name}")
        seen_ids.add(profile_id)
        profiles.append(profile)
    if not profiles:
        raise ValueError("The starter profile catalog is empty.")
    return profiles


def install_starter_profiles(
    manager: AgentManager,
    *,
    owner_user_id: int,
    default_model_id: int | None = None,
    publish: bool = False,
) -> dict[str, Any]:
    """Add missing starter agents without changing any existing agent."""
    if not isinstance(publish, bool):
        raise ValueError("The publish option must be a boolean.")
    if default_model_id is not None:
        try:
            default_model_id = int(default_model_id)
        except (TypeError, ValueError) as error:
            raise ValueError("Default model ID must be an integer.") from error
        if default_model_id <= 0:
            raise ValueError("Default model ID must be a positive integer.")

    profiles = load_starter_profiles()
    agents = manager.list_agents()
    by_profile_id = {agent.starter_profile_id: agent for agent in agents if agent.starter_profile_id}
    by_name = {agent.name.casefold(): agent for agent in agents}
    results: list[dict[str, Any]] = []
    installed = skipped = conflicts = 0

    for profile in profiles:
        profile_id = profile["profile_id"]
        name = profile["name"]
        if profile_id in by_profile_id:
            skipped += 1
            results.append({"profile_id": profile_id, "name": name, "status": "already_installed"})
            continue
        if name.casefold() in by_name:
            conflicts += 1
            results.append({"profile_id": profile_id, "name": name, "status": "name_conflict"})
            continue

        agent = manager.create_agent(
            name,
            **profile["prompt"],
            owner_user_id=owner_user_id,
            mode=DEFAULT_AGENT_MODE,
            default_model_id=default_model_id,
            is_public=publish,
            starter_profile_id=profile_id,
            system_prompt_id=0,
            memory_id=0,
            rag_root_ids=[],
            tool_ids=[],
            knowledge_root="",
            metadata={},
        )
        installed += 1
        by_profile_id[profile_id] = agent
        by_name[name.casefold()] = agent
        results.append({"profile_id": profile_id, "name": name, "status": "installed", "agent_id": agent.id})

    return {
        "status": "installed" if installed else "unchanged",
        "installed": installed,
        "already_installed": skipped,
        "name_conflicts": conflicts,
        "published": bool(publish),
        "default_model_id": default_model_id,
        "profiles": results,
    }
