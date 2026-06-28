from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.core.app_config import get_config_value, load_app_config, save_app_config
from src.lib.apmatia_core.models import utc_now
from src.lib.discussions.prompt_llm import prompt_llm

from .models import LLM


def _normalize_llm_record(item: dict) -> dict:
    if "user_alias" not in item:
        item["user_alias"] = item.pop("name", "")
    if "provider_name" not in item:
        item["provider_name"] = item.pop("model_name", item.pop("provider_model_name", ""))
    item.pop("provider_model_name", None)
    item["id"] = _parse_int(item.get("id"))
    item["owner_user_id"] = _parse_int(item.get("owner_user_id"))
    item["owner_group_id"] = _parse_int(item.get("owner_group_id"))
    item["mode"] = _parse_int(item.get("mode"), default=0) or 0
    item["created_at"] = _parse_datetime(item.get("created_at"))
    item["updated_at"] = _parse_datetime(item.get("updated_at"))
    return item


def _parse_int(value, default=None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not value:
        return utc_now()
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return utc_now()
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _serialize_llm_record(config: LLM) -> dict:
    return {
        "id": _parse_int(config.id),
        "owner_user_id": config.owner_user_id,
        "owner_group_id": config.owner_group_id,
        "mode": config.mode,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
        "user_alias": config.user_alias,
        "metadata": dict(config.metadata),
        "backend": config.backend,
        "provider_name": config.provider_name,
        "model_url": config.model_url,
        "api_key": config.api_key,
        "max_response_size": config.max_response_size,
        "system_prompt": config.system_prompt,
    }


class LLMManager:
    """Persist and manage LLM configs in the shared app config."""

    def _load_configs(self) -> list[dict]:
        configs = get_config_value("llm", "configs", default=[])
        if not isinstance(configs, list):
            return []
        return [_normalize_llm_record(dict(item)) for item in configs if isinstance(item, dict)]

    def _save_configs(self, configs: list[dict]) -> None:
        config = load_app_config()
        config.setdefault("llm", {})
        config["llm"]["configs"] = [
            _serialize_llm_record(
                item if isinstance(item, LLM) else LLM(**_normalize_llm_record(dict(item)))
            )
            for item in configs
            if isinstance(item, (dict, LLM))
        ]
        save_app_config(config)

    def list_configs(self) -> list[LLM]:
        return [LLM(**item) for item in self._load_configs()]

    def get_config(self, config_id: int) -> LLM | None:
        for config in self.list_configs():
            if int(config.id or -1) == config_id:
                return config
        return None

    def create_config(self, config: LLM) -> LLM:
        configs = self._load_configs()
        next_id = max((int(item.get("id", 0)) for item in configs), default=0) + 1
        now = utc_now()
        created = replace(
            config,
            id=next_id,
            created_at=config.created_at or now,
            updated_at=now,
        )
        configs.append(_serialize_llm_record(created))
        self._save_configs(configs)
        return created

    def update_config(self, config_id: int, **updates) -> LLM:
        configs = self._load_configs()
        normalized_updates = _normalize_llm_record(dict(updates))
        for index, item in enumerate(configs):
            if int(item.get("id", -1)) != config_id:
                continue
            existing = LLM(**item)
            merged = replace(
                existing,
                owner_user_id=normalized_updates.get("owner_user_id", existing.owner_user_id),
                owner_group_id=normalized_updates.get("owner_group_id", existing.owner_group_id),
                mode=normalized_updates.get("mode", existing.mode),
                user_alias=normalized_updates.get("user_alias", existing.user_alias),
                metadata=normalized_updates.get("metadata", existing.metadata),
                backend=normalized_updates.get("backend", existing.backend),
                provider_name=normalized_updates.get("provider_name", existing.provider_name),
                model_url=normalized_updates.get("model_url", existing.model_url),
                api_key=normalized_updates.get("api_key", existing.api_key),
                max_response_size=normalized_updates.get("max_response_size", existing.max_response_size),
                system_prompt=normalized_updates.get("system_prompt", existing.system_prompt),
                created_at=normalized_updates.get("created_at", existing.created_at),
                updated_at=utc_now(),
            )
            configs[index] = _serialize_llm_record(merged)
            self._save_configs(configs)
            return merged
        raise ValueError(f"LLM not found: {config_id}")

    def delete_config(self, config_id: int) -> bool:
        configs = self._load_configs()
        next_configs = [item for item in configs if int(item.get("id", -1)) != config_id]
        if len(next_configs) == len(configs):
            return False
        self._save_configs(next_configs)
        return True

    def probe_config(self, config_id: int) -> dict:
        config = self.get_config(config_id)
        if config is None:
            raise ValueError(f"LLM not found: {config_id}")

        limited_config = replace(
            config,
            max_response_size=max(16, min(int(config.max_response_size or 64), 64)),
        )
        reply = prompt_llm(
            prompt=(
                "Reply in one short sentence, under 30 words, confirming connectivity "
                "and include the word ready exactly once."
            ),
            llm_config=limited_config,
        ).strip()
        preview = reply[:240]
        return {
            "config_id": int(config_id),
            "user_alias": config.user_alias,
            "model_url": config.model_url,
            "reply_preview": preview,
            "reply_length": len(reply),
        }
