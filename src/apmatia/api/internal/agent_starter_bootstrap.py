"""One-time installation of Apmatia's built-in public starter agents."""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from apmatia.core.app_config import get_config_value, set_config_value
from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.modules.agents.runtime import get_agent_manager
from apmatia.modules.agents.starter_catalog import install_starter_profiles, load_starter_profiles


_logger = logging.getLogger(__name__)
_lock = Lock()
_SEEDED_KEY = "default_starters_seeded_v1"


def ensure_default_starter_agents(owner_user_id: int) -> dict[str, Any] | None:
    """Install and publish the curated starter agents once a backing model exists.

    The first configured Apmatia model is assigned only where a starter has no
    valid selection. Existing prompt/name/model customizations are preserved.
    A persistent marker prevents deleted starters from being recreated.
    """
    with _lock:
        try:
            if get_config_value("agents", _SEEDED_KEY, default=False):
                return None

            configs = get_llm_config_manager().list_configs()
            model = next(
                (
                    config
                    for config in configs
                    if isinstance(getattr(config, "id", None), int)
                    and isinstance(getattr(config, "provider_name", None), str)
                    and config.provider_name.strip()
                ),
                None,
            )
            if model is None:
                return None

            manager = get_agent_manager()
            result = install_starter_profiles(
                manager,
                owner_user_id=int(owner_user_id),
                default_model_id=model.id,
                publish=True,
            )
            profile_ids = {profile["profile_id"] for profile in load_starter_profiles()}
            for agent in manager.list_agents():
                if agent.starter_profile_id not in profile_ids:
                    continue
                updates: dict[str, Any] = {}
                if not agent.is_public:
                    updates["is_public"] = True
                if agent.active_model_id is None and agent.default_model_id is None:
                    updates["default_model_id"] = model.id
                if updates:
                    manager.update_agent(agent.id, **updates)

            set_config_value("agents", _SEEDED_KEY, value=True)
            _logger.info(
                "default starter agents installed count=%s updated=%s owner=%s",
                result["installed"],
                result["already_installed"],
                owner_user_id,
            )
            return result
        except Exception:
            _logger.exception("failed to install default starter agents")
            return None


def seed_default_starters_for_first_user() -> dict[str, Any] | None:
    """Seed once at startup when a user and an Apmatia model are configured."""
    try:
        from apmatia.modules.users.runtime import get_user_manager

        users = [user for user in get_user_manager().list_users() if getattr(user, "id", None) is not None]
        if not users:
            return None
        first_user = min(users, key=lambda user: int(user.id))
        return ensure_default_starter_agents(int(first_user.id))
    except Exception:
        _logger.exception("failed to check for default starter agent installation")
        return None
