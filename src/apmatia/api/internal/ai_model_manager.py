from __future__ import annotations

from apmatia.modules.ai_model_manager import AIModelManager, GGUFModelRecord, TaskSizePreference
from apmatia.modules.ai_model_manager.services import format_bytes


def _model_to_dict(model: GGUFModelRecord) -> dict:
    return {
        "id": model.id,
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


def _preference_to_dict(preference: TaskSizePreference) -> dict:
    return {
        "id": preference.id,
        "task_name": preference.task_name,
        "preferred_size_classes": list(preference.preferred_size_classes),
        "notes": preference.notes,
    }


def list_ai_models() -> list[dict]:
    manager = AIModelManager()
    return [_model_to_dict(model) for model in manager.list_models()]


def create_ai_model(**payload) -> dict:
    manager = AIModelManager()
    model = manager.create_model(GGUFModelRecord(**payload))
    return _model_to_dict(model)


def update_ai_model(model_id: int, **updates) -> dict:
    manager = AIModelManager()
    model = manager.update_model(model_id, **updates)
    return _model_to_dict(model)


def delete_ai_model(model_id: int) -> bool:
    manager = AIModelManager()
    return manager.delete_model(model_id)


def show_ai_model(model_id: int) -> dict:
    manager = AIModelManager()
    model = manager.get_model(model_id)
    if model is None:
        raise ValueError(f"GGUF model not found: {model_id}")
    return _model_to_dict(model)


def scan_ai_models(directory: str, *, recursive: bool = True) -> dict:
    manager = AIModelManager()
    return manager.scan_gguf_directory(directory, recursive=recursive)


def list_task_preferences() -> list[dict]:
    manager = AIModelManager()
    return [_preference_to_dict(item) for item in manager.list_task_preferences()]


def create_task_preference(**payload) -> dict:
    manager = AIModelManager()
    preference = manager.upsert_task_preference(TaskSizePreference(**payload))
    return _preference_to_dict(preference)


def update_task_preference(preference_id: int, **updates) -> dict:
    manager = AIModelManager()
    preference = manager.update_task_preference(preference_id, **updates)
    return _preference_to_dict(preference)


def delete_task_preference(preference_id: int) -> bool:
    manager = AIModelManager()
    return manager.delete_task_preference(preference_id)
