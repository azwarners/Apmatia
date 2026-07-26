from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .models import GGUFModelRecord, LLMConfig, TaskSizePreference
from .services import AIModelManager, format_bytes, list_llm_configs, create_llm_config, update_llm_config, delete_llm_config, probe_llm_config, get_llm_config


class ApmatiaAiModelManagerModuleViewProvider:
    def __init__(self, manager: AIModelManager | None = None):
        self._manager = manager or AIModelManager()

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        if object_type == "gguf_model":
            items = sorted(
                self._manager.list_models(),
                key=lambda item: (
                    int(item.file_size_bytes or 0),
                    str(item.name).lower(),
                    int(item.id or 0),
                ),
            )
            return [_model_to_dict(item) for item in items]
        if object_type == "task_preference":
            items = sorted(self._manager.list_task_preferences(), key=lambda item: (str(item.task_name).lower(), int(item.id or 0)))
            return [_preference_to_dict(item) for item in items]
        if object_type == "llm_config":
            items = list_llm_configs()
            return [_llm_config_to_dict(item) for item in items]
        raise ValueError(f"Unsupported ai model manager object type: {object_type}")

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)

        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if object_type == "gguf_model" and verb == "scan":
            return self._scan(payload)
        if object_type == "gguf_model" and verb == "show":
            return self._show(payload)
        if object_type == "gguf_model" and verb == "create":
            return self._create_model(payload)
        if object_type == "gguf_model" and verb == "edit":
            return self._edit_model(payload)
        if object_type == "gguf_model" and verb == "delete":
            return self._delete_model(payload)
        if object_type == "task_preference" and verb == "create":
            return self._create_preference(payload)
        if object_type == "task_preference" and verb == "edit":
            return self._edit_preference(payload)
        if object_type == "task_preference" and verb == "delete":
            return self._delete_preference(payload)
        if object_type == "llm_config" and verb == "create":
            return self._create_llm_config(payload)
        if object_type == "llm_config" and verb == "edit":
            return self._edit_llm_config(payload)
        if object_type == "llm_config" and verb == "delete":
            return self._delete_llm_config(payload)
        if object_type == "llm_config" and verb == "test":
            return self._test_llm_config(payload)
        raise ValueError(f"Unsupported module command verb for now: {verb}")

    def _scan(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        directory = _required_path(payload.get("directory"))
        recursive = bool(payload.get("recursive", True))
        return self._manager.scan_gguf_directory(directory, recursive=recursive)

    def _show(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model_id = _require_int(payload.get("item_id"))
        model = self._manager.get_model(model_id)
        if model is None:
            raise ValueError(f"GGUF model not found: {model_id}")
        data = _model_to_dict(model)
        data["path_exists"] = Path(str(model.local_path)).exists()
        return data

    def _create_model(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model = _model_from_payload(payload)
        if not model.local_path:
            raise ValueError("A local_path is required for a GGUF model.")
        created = self._manager.create_model(model)
        return {"status": "created", "item": _model_to_dict(created)}

    def _edit_model(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model_id = _require_int(payload.get("item_id"))
        updates = dict(payload)
        updates.pop("item_id", None)
        updated = self._manager.update_model(model_id, **_model_update_payload(updates))
        return {"status": "updated", "item": _model_to_dict(updated)}

    def _delete_model(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model_id = _require_int(payload.get("item_id"))
        deleted = self._manager.delete_model(model_id)
        return {"status": "deleted" if deleted else "not_found", "item_id": model_id, "deleted": deleted}

    def _create_preference(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        preference = _preference_from_payload(payload)
        if not preference.task_name:
            raise ValueError("A task_name is required for a preference.")
        if not preference.preferred_size_classes:
            raise ValueError("At least one preferred size class is required.")
        created = self._manager.upsert_task_preference(preference)
        return {"status": "created", "item": _preference_to_dict(created)}

    def _edit_preference(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        preference_id = _require_int(payload.get("item_id"))
        updates = dict(payload)
        updates.pop("item_id", None)
        updated = self._manager.update_task_preference(preference_id, **_preference_update_payload(updates))
        return {"status": "updated", "item": _preference_to_dict(updated)}

    def _delete_preference(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        preference_id = _require_int(payload.get("item_id"))
        deleted = self._manager.delete_task_preference(preference_id)
        return {"status": "deleted" if deleted else "not_found", "item_id": preference_id, "deleted": deleted}

    def _create_llm_config(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        config = _llm_config_from_payload(payload)
        if not config.model_url:
            raise ValueError("A model_url is required for an LLM config.")
        created = create_llm_config(config)
        return {"status": "created", "item": _llm_config_to_dict(created)}

    def _edit_llm_config(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        config_id = _require_int(payload.get("item_id"))
        updates = dict(payload)
        updates.pop("item_id", None)
        if updates.get("api_key") == "":
            existing = get_llm_config(config_id)
            if existing:
                updates["api_key"] = existing.api_key
        updated = update_llm_config(config_id, **_llm_config_update_payload(updates))
        return {"status": "updated", "item": _llm_config_to_dict(updated)}

    def _delete_llm_config(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        config_id = _require_int(payload.get("item_id"))
        deleted = delete_llm_config(config_id)
        return {"status": "deleted" if deleted else "not_found", "item_id": config_id, "deleted": deleted}

    def _test_llm_config(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        config_id = _require_int(payload.get("item_id"))
        result = probe_llm_config(config_id)
        return {"status": "ok", "item": result}


def _view_from_command(command: CommandContribution) -> ViewContribution:
    view_id = str(command.metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=view_id,
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )


def _object_type(metadata: Mapping[str, Any]) -> str:
    object_type = str(metadata.get("object_type") or "").strip()
    if not object_type:
        raise ValueError("Module metadata is missing object_type.")
    return object_type


def _command_verb(command_id: str) -> str:
    parts = [part for part in str(command_id).split(".") if part]
    return "" if not parts else parts[-1].lower()


def _require_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid item ID is required.") from error


def _required_path(value: Any) -> str:
    path = str(value or "").strip()
    if not path:
        raise ValueError("A directory path is required.")
    return path


def _parse_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_size_classes(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _model_from_payload(payload: Mapping[str, Any]) -> GGUFModelRecord:
    return GGUFModelRecord(
        id=_parse_int(payload.get("id")),
        name=str(payload.get("name") or "").strip(),
        local_path=str(payload.get("local_path") or "").strip(),
        file_size_bytes=_parse_int(payload.get("file_size_bytes"), default=0) or 0,
        estimated_ram_bytes=_parse_int(payload.get("estimated_ram_bytes"), default=0) or 0,
        estimated_vram_bytes=_parse_int(payload.get("estimated_vram_bytes"), default=0) or 0,
        size_class=str(payload.get("size_class") or "").strip(),
        cost_mode=str(payload.get("cost_mode") or "free").strip() or "free",
        input_token_cost_per_1k=_parse_float(payload.get("input_token_cost_per_1k")),
        output_token_cost_per_1k=_parse_float(payload.get("output_token_cost_per_1k")),
        notes=str(payload.get("notes") or "").strip(),
        metadata=dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {},
    )


def _model_update_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(payload.get("name") or "").strip(),
        "local_path": str(payload.get("local_path") or "").strip(),
        "file_size_bytes": _parse_int(payload.get("file_size_bytes"), default=0) or 0,
        "estimated_ram_bytes": _parse_int(payload.get("estimated_ram_bytes"), default=0) or 0,
        "estimated_vram_bytes": _parse_int(payload.get("estimated_vram_bytes"), default=0) or 0,
        "size_class": str(payload.get("size_class") or "").strip(),
        "cost_mode": str(payload.get("cost_mode") or "free").strip() or "free",
        "input_token_cost_per_1k": _parse_float(payload.get("input_token_cost_per_1k")),
        "output_token_cost_per_1k": _parse_float(payload.get("output_token_cost_per_1k")),
        "notes": str(payload.get("notes") or "").strip(),
        "metadata": dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {},
    }


def _preference_from_payload(payload: Mapping[str, Any]) -> TaskSizePreference:
    return TaskSizePreference(
        id=_parse_int(payload.get("id")),
        task_name=str(payload.get("task_name") or "").strip(),
        preferred_size_classes=_parse_size_classes(payload.get("preferred_size_classes")),
        notes=str(payload.get("notes") or "").strip(),
    )


def _preference_update_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_name": str(payload.get("task_name") or "").strip(),
        "preferred_size_classes": _parse_size_classes(payload.get("preferred_size_classes")),
        "notes": str(payload.get("notes") or "").strip(),
    }


def _model_to_dict(model: GGUFModelRecord) -> dict[str, Any]:
    return {
        "id": model.id,
        "owner_user_id": model.owner_user_id,
        "owner_group_id": model.owner_group_id,
        "mode": model.mode,
        "created_at": model.created_at.isoformat(),
        "updated_at": model.updated_at.isoformat(),
        "name": model.name,
        "local_path": model.local_path,
        "file_size_bytes": model.file_size_bytes,
        "file_size_human": format_bytes(model.file_size_bytes),
        "size_class": model.size_class,
        "vision_enabled": model.vision_enabled,
        "cost_mode": model.cost_mode,
        "input_token_cost_per_1k": model.input_token_cost_per_1k,
        "output_token_cost_per_1k": model.output_token_cost_per_1k,
        "notes": model.notes,
        "metadata": dict(model.metadata),
    }


def _preference_to_dict(preference: TaskSizePreference) -> dict[str, Any]:
    return {
        "id": preference.id,
        "owner_user_id": preference.owner_user_id,
        "owner_group_id": preference.owner_group_id,
        "mode": preference.mode,
        "created_at": preference.created_at.isoformat(),
        "updated_at": preference.updated_at.isoformat(),
        "task_name": preference.task_name,
        "preferred_size_classes": list(preference.preferred_size_classes),
        "notes": preference.notes,
    }


def _llm_config_from_payload(payload: Mapping[str, Any]) -> LLMConfig:
    return LLMConfig(
        id=_parse_int(payload.get("id")),
        user_alias=str(payload.get("user_alias") or "").strip(),
        backend=str(payload.get("backend") or "openai_compatible").strip() or "openai_compatible",
        provider_name=str(payload.get("provider_name") or "").strip(),
        model_url=str(payload.get("model_url") or "").strip(),
        api_key=str(payload.get("api_key") or "").strip(),
        max_response_size=_parse_int(payload.get("max_response_size"), default=8192) or 8192,
        seats=_parse_int(payload.get("seats"), default=1) or 1,
        system_prompt=str(payload.get("system_prompt") or "").strip(),
        metadata=dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {},
    )


def _llm_config_update_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "user_alias": str(payload.get("user_alias") or "").strip(),
        "backend": str(payload.get("backend") or "openai_compatible").strip() or "openai_compatible",
        "provider_name": str(payload.get("provider_name") or "").strip(),
        "model_url": str(payload.get("model_url") or "").strip(),
        "api_key": str(payload.get("api_key") or "").strip(),
        "max_response_size": _parse_int(payload.get("max_response_size"), default=8192) or 8192,
        "seats": _parse_int(payload.get("seats"), default=1) or 1,
        "system_prompt": str(payload.get("system_prompt") or "").strip(),
        "metadata": dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {},
    }


def _llm_config_to_dict(config: LLMConfig) -> dict[str, Any]:
    return {
        "id": config.id,
        "owner_user_id": config.owner_user_id,
        "owner_group_id": config.owner_group_id,
        "mode": config.mode,
        "created_at": config.created_at.isoformat() if config.created_at else "",
        "updated_at": config.updated_at.isoformat() if config.updated_at else "",
        "user_alias": config.user_alias,
        "backend": config.backend,
        "provider_name": config.provider_name,
        "model_url": config.model_url,
        "api_key": config.api_key,
        "max_response_size": config.max_response_size,
        "seats": config.seats,
        "system_prompt": config.system_prompt,
        "metadata": dict(config.metadata),
    }
