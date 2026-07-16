from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Iterable

from apmatia.core.app_config import get_config_value, load_app_config, save_app_config
from apmatia.lib.apmatia_core.models import utc_now

from .models import GGUFModelRecord, TaskSizePreference

_MODELS_KEY = ("ai_model_manager", "models")
_TASK_PREFERENCES_KEY = ("ai_model_manager", "task_preferences")
_SHARD_SUFFIX_RE = re.compile(r"^(?P<base>.+)-(?P<part>\d+)-of-(?P<total>\d+)$", re.IGNORECASE)

_SIZE_CLASS_RAM_MULTIPLIERS = {
    "small": 1.6,
    "medium": 2.0,
    "large": 2.6,
    "xlarge": 3.2,
}


def _parse_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _parse_datetime(value: Any) -> datetime:
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


def _split_size_classes(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_text(item) for item in value if _normalize_text(item))
    return tuple(part for part in (_normalize_text(part) for part in str(value).split(",")) if part)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _path_key(path: Path) -> str:
    return str(path.expanduser().resolve())


def _is_mmproj_file(path: Path) -> bool:
    stem = path.stem.lower()
    return bool(re.search(r"(^|[._-])mmproj([._-]|$)", stem, re.IGNORECASE))


def _shard_parts(path: Path) -> tuple[str, int, int] | None:
    match = _SHARD_SUFFIX_RE.match(path.stem)
    if not match:
        return None
    try:
        return match.group("base"), int(match.group("part")), int(match.group("total"))
    except ValueError:
        return None


def _normalize_model_record(item: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    item["id"] = _parse_int(item.get("id"))
    item["owner_user_id"] = _parse_int(item.get("owner_user_id"))
    item["owner_group_id"] = _parse_int(item.get("owner_group_id"))
    item["mode"] = _parse_int(item.get("mode"), default=0) or 0
    item["created_at"] = _parse_datetime(item.get("created_at"))
    item["updated_at"] = _parse_datetime(item.get("updated_at"))
    item["name"] = _normalize_text(item.get("name"))
    item["local_path"] = _normalize_text(item.get("local_path"))
    item["file_size_bytes"] = _parse_int(item.get("file_size_bytes"), default=0) or 0
    item["estimated_ram_bytes"] = _parse_int(item.get("estimated_ram_bytes"), default=0) or 0
    item["estimated_vram_bytes"] = _parse_int(item.get("estimated_vram_bytes"), default=0) or 0
    item["size_class"] = _normalize_text(item.get("size_class"))
    item["vision_enabled"] = _parse_bool(item.get("vision_enabled"), default=False)
    item["cost_mode"] = _normalize_text(item.get("cost_mode")) or "free"
    item["input_token_cost_per_1k"] = _parse_float(item.get("input_token_cost_per_1k"))
    item["output_token_cost_per_1k"] = _parse_float(item.get("output_token_cost_per_1k"))
    item["notes"] = _normalize_text(item.get("notes"))
    metadata = item.get("metadata")
    item["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    item["vision_enabled"] = bool(item["vision_enabled"]) or bool(item["metadata"].get("mmproj_paths"))
    return item


def _normalize_task_preference(item: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    item["id"] = _parse_int(item.get("id"))
    item["owner_user_id"] = _parse_int(item.get("owner_user_id"))
    item["owner_group_id"] = _parse_int(item.get("owner_group_id"))
    item["mode"] = _parse_int(item.get("mode"), default=0) or 0
    item["created_at"] = _parse_datetime(item.get("created_at"))
    item["updated_at"] = _parse_datetime(item.get("updated_at"))
    item["task_name"] = _normalize_text(item.get("task_name"))
    item["preferred_size_classes"] = _split_size_classes(item.get("preferred_size_classes"))
    item["notes"] = _normalize_text(item.get("notes"))
    return item


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _serialize_model_record(record: GGUFModelRecord | dict[str, Any]) -> dict[str, Any]:
    data = record if isinstance(record, dict) else asdict(record)
    normalized = _normalize_model_record(dict(data))
    return {
        "id": normalized["id"],
        "owner_user_id": normalized["owner_user_id"],
        "owner_group_id": normalized["owner_group_id"],
        "mode": normalized["mode"],
        "created_at": _serialize_datetime(normalized["created_at"]),
        "updated_at": _serialize_datetime(normalized["updated_at"]),
        "name": normalized["name"],
        "local_path": normalized["local_path"],
        "file_size_bytes": normalized["file_size_bytes"],
        "estimated_ram_bytes": normalized["estimated_ram_bytes"],
        "estimated_vram_bytes": normalized["estimated_vram_bytes"],
        "size_class": normalized["size_class"],
        "vision_enabled": normalized["vision_enabled"],
        "cost_mode": normalized["cost_mode"],
        "input_token_cost_per_1k": normalized["input_token_cost_per_1k"],
        "output_token_cost_per_1k": normalized["output_token_cost_per_1k"],
        "notes": normalized["notes"],
        "metadata": dict(normalized["metadata"]),
    }


def _serialize_task_preference(record: TaskSizePreference | dict[str, Any]) -> dict[str, Any]:
    data = record if isinstance(record, dict) else asdict(record)
    normalized = _normalize_task_preference(dict(data))
    return {
        "id": normalized["id"],
        "owner_user_id": normalized["owner_user_id"],
        "owner_group_id": normalized["owner_group_id"],
        "mode": normalized["mode"],
        "created_at": _serialize_datetime(normalized["created_at"]),
        "updated_at": _serialize_datetime(normalized["updated_at"]),
        "task_name": normalized["task_name"],
        "preferred_size_classes": list(normalized["preferred_size_classes"]),
        "notes": normalized["notes"],
    }


def _load_model_items() -> list[dict[str, Any]]:
    models = get_config_value(*_MODELS_KEY, default=[])
    if not isinstance(models, list):
        return []
    return [_normalize_model_record(dict(item)) for item in models if isinstance(item, dict)]


def _load_task_preferences() -> list[dict[str, Any]]:
    preferences = get_config_value(*_TASK_PREFERENCES_KEY, default=[])
    if not isinstance(preferences, list):
        return []
    return [_normalize_task_preference(dict(item)) for item in preferences if isinstance(item, dict)]


def _save_model_items(items: list[dict[str, Any]]) -> None:
    config = load_app_config()
    config.setdefault("ai_model_manager", {})
    config["ai_model_manager"]["models"] = [
        _serialize_model_record(item if isinstance(item, dict) else dict(item))
        for item in items
    ]
    save_app_config(config)


def _save_task_preferences(items: list[dict[str, Any]]) -> None:
    config = load_app_config()
    config.setdefault("ai_model_manager", {})
    config["ai_model_manager"]["task_preferences"] = [
        _serialize_task_preference(item if isinstance(item, dict) else dict(item))
        for item in items
    ]
    save_app_config(config)


class AIModelManager:
    def list_models(self) -> list[GGUFModelRecord]:
        self._bootstrap_from_configured_directory()
        items = _load_model_items()
        items = sorted(
            items,
            key=lambda item: (
                int(item.get("file_size_bytes", 0) or 0),
                str(item.get("name") or "").lower(),
                int(item.get("id", 0) or 0),
            ),
        )
        return [GGUFModelRecord(**item) for item in items]

    def get_model(self, model_id: int) -> GGUFModelRecord | None:
        for item in _load_model_items():
            model = GGUFModelRecord(**item)
            if int(model.id or -1) == int(model_id):
                return model
        return None

    def get_model_by_path(self, local_path: str) -> GGUFModelRecord | None:
        normalized = str(Path(local_path).expanduser().resolve())
        for item in _load_model_items():
            if str(item.get("local_path") or "") == normalized:
                return GGUFModelRecord(**item)
        return None

    def create_model(self, model: GGUFModelRecord) -> GGUFModelRecord:
        if not str(model.local_path or "").strip():
            raise ValueError("local_path is required for a GGUF model.")
        items = _load_model_items()
        next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
        now = utc_now()
        created = replace(model, id=next_id, created_at=model.created_at or now, updated_at=now)
        items.append(_serialize_model_record(created))
        _save_model_items(items)
        return created

    def update_model(self, model_id: int, **updates: Any) -> GGUFModelRecord:
        items = _load_model_items()
        for index, item in enumerate(items):
            if int(item.get("id", -1)) != int(model_id):
                continue
            existing = GGUFModelRecord(**item)
            merged = replace(
                existing,
                owner_user_id=_update_int(updates, "owner_user_id", existing.owner_user_id),
                owner_group_id=_update_int(updates, "owner_group_id", existing.owner_group_id),
                mode=_update_int(updates, "mode", existing.mode) or 0,
                name=_update_text(updates, "name", existing.name),
                local_path=_update_text(updates, "local_path", existing.local_path),
                file_size_bytes=_update_int(updates, "file_size_bytes", existing.file_size_bytes) or 0,
                estimated_ram_bytes=_update_int(updates, "estimated_ram_bytes", existing.estimated_ram_bytes) or 0,
                estimated_vram_bytes=_update_int(updates, "estimated_vram_bytes", existing.estimated_vram_bytes) or 0,
                size_class=_update_text(updates, "size_class", existing.size_class),
                vision_enabled=_update_bool(updates, "vision_enabled", existing.vision_enabled),
                cost_mode=_update_text(updates, "cost_mode", existing.cost_mode) or existing.cost_mode,
                input_token_cost_per_1k=_update_float(updates, "input_token_cost_per_1k", existing.input_token_cost_per_1k),
                output_token_cost_per_1k=_update_float(updates, "output_token_cost_per_1k", existing.output_token_cost_per_1k),
                notes=_update_text(updates, "notes", existing.notes),
                metadata=_update_metadata(updates, "metadata", existing.metadata),
                created_at=existing.created_at,
                updated_at=utc_now(),
            )
            items[index] = _serialize_model_record(merged)
            _save_model_items(items)
            return merged
        raise ValueError(f"GGUF model not found: {model_id}")

    def delete_model(self, model_id: int) -> bool:
        items = _load_model_items()
        next_items = [item for item in items if int(item.get("id", -1)) != int(model_id)]
        if len(next_items) == len(items):
            return False
        _save_model_items(next_items)
        return True

    def list_task_preferences(self) -> list[TaskSizePreference]:
        return [TaskSizePreference(**item) for item in _load_task_preferences()]

    def get_task_preference(self, preference_id: int) -> TaskSizePreference | None:
        for preference in self.list_task_preferences():
            if int(preference.id or -1) == int(preference_id):
                return preference
        return None

    def upsert_task_preference(self, preference: TaskSizePreference) -> TaskSizePreference:
        items = _load_task_preferences()
        now = utc_now()
        if preference.id is None:
            if not str(preference.task_name or "").strip():
                raise ValueError("task_name is required for a task preference.")
            if not preference.preferred_size_classes:
                raise ValueError("preferred_size_classes is required for a task preference.")
            next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
            created = replace(preference, id=next_id, created_at=preference.created_at or now, updated_at=now)
            items.append(_serialize_task_preference(created))
            _save_task_preferences(items)
            return created

        for index, item in enumerate(items):
            if int(item.get("id", -1)) != int(preference.id):
                continue
            merged = replace(preference, updated_at=now, created_at=_parse_datetime(item.get("created_at")))
            items[index] = _serialize_task_preference(merged)
            _save_task_preferences(items)
            return merged

        created = replace(preference, updated_at=now, created_at=preference.created_at or now)
        items.append(_serialize_task_preference(created))
        _save_task_preferences(items)
        return created

    def update_task_preference(self, preference_id: int, **updates: Any) -> TaskSizePreference:
        items = _load_task_preferences()
        for index, item in enumerate(items):
            if int(item.get("id", -1)) != int(preference_id):
                continue
            existing = TaskSizePreference(**item)
            merged = replace(
                existing,
                owner_user_id=_update_int(updates, "owner_user_id", existing.owner_user_id),
                owner_group_id=_update_int(updates, "owner_group_id", existing.owner_group_id),
                mode=_update_int(updates, "mode", existing.mode) or 0,
                task_name=_update_text(updates, "task_name", existing.task_name),
                preferred_size_classes=_update_size_classes(updates, "preferred_size_classes", existing.preferred_size_classes),
                notes=_update_text(updates, "notes", existing.notes),
                created_at=existing.created_at,
                updated_at=utc_now(),
            )
            items[index] = _serialize_task_preference(merged)
            _save_task_preferences(items)
            return merged
        raise ValueError(f"Task preference not found: {preference_id}")

    def delete_task_preference(self, preference_id: int) -> bool:
        items = _load_task_preferences()
        next_items = [item for item in items if int(item.get("id", -1)) != int(preference_id)]
        if len(next_items) == len(items):
            return False
        _save_task_preferences(next_items)
        return True

    def scan_gguf_directory(self, directory: str | Path, *, recursive: bool = True) -> dict[str, Any]:
        directory_path = Path(directory).expanduser()
        if not directory_path.exists():
            raise ValueError(f"GGUF directory not found: {directory_path}")
        if not directory_path.is_dir():
            raise ValueError(f"GGUF scan target is not a directory: {directory_path}")

        matches = list(_iter_gguf_files(directory_path, recursive=recursive))
        companion_paths_by_dir: dict[str, list[str]] = {}
        group_files: dict[str, list[Path]] = {}
        primary_paths: dict[str, Path] = {}
        for path in matches:
            if _is_mmproj_file(path):
                companion_paths_by_dir.setdefault(_path_key(path.parent), []).append(_path_key(path))
                continue
            shard_parts = _shard_parts(path)
            if shard_parts is not None:
                group_key = f"{_path_key(path.parent)}::{shard_parts[0]}::{shard_parts[2]}"
                group_files.setdefault(group_key, []).append(path)
                if shard_parts[1] == 1:
                    primary_paths[group_key] = path
                continue
            group_key = f"{_path_key(path.parent)}::{path.stem}"
            group_files.setdefault(group_key, []).append(path)
            primary_paths.setdefault(group_key, path)

        existing_models = {
            _path_key(Path(str(item.get("local_path") or ""))): item
            for item in _load_model_items()
            if str(item.get("local_path") or "").strip()
        }
        created = 0
        updated = 0
        scanned_models: list[GGUFModelRecord] = []

        for group_key, path in sorted(
            primary_paths.items(),
            key=lambda item: (
                int(item[1].stat().st_size),
                str(item[1]).lower(),
            ),
        ):
            scanned = self._record_for_path(
                path,
                group_files=group_files.get(group_key, ()),
                companion_paths=companion_paths_by_dir.get(_path_key(path.parent), ()),
            )
            existing = existing_models.get(scanned.local_path)
            if existing is None:
                created_model = self.create_model(scanned)
                created += 1
                scanned_models.append(created_model)
                continue
            merged = self.update_model(
                int(existing["id"]),
                name=scanned.name or str(existing.get("name") or ""),
                local_path=scanned.local_path,
                file_size_bytes=scanned.file_size_bytes,
                estimated_ram_bytes=scanned.estimated_ram_bytes,
                estimated_vram_bytes=scanned.estimated_vram_bytes,
                size_class=scanned.size_class or str(existing.get("size_class") or ""),
                vision_enabled=bool(scanned.metadata.get("mmproj_paths")),
                metadata={**dict(existing.get("metadata") or {}), **scanned.metadata},
            )
            updated += 1
            scanned_models.append(merged)

        removed = self._purge_non_primary_scan_records(matches)
        scanned_models = sorted(
            scanned_models,
            key=lambda item: (
                int(item.file_size_bytes or 0),
                str(item.name).lower(),
                int(item.id or 0),
            ),
        )

        return {
            "directory": str(directory_path),
            "recursive": bool(recursive),
            "scanned": len(primary_paths),
            "discovered": len(matches),
            "created": created,
            "updated": updated,
            "removed": removed,
            "items": [self._model_to_dict(item) for item in scanned_models],
        }

    def _record_for_path(
        self,
        path: Path,
        *,
        group_files: Iterable[Path] = (),
        companion_paths: Iterable[str] = (),
    ) -> GGUFModelRecord:
        group_list = [Path(item) for item in group_files] or [path]
        file_size_bytes = sum(item.stat().st_size for item in group_list)
        size_class = infer_size_class(path.name, file_size_bytes)
        estimated_ram_bytes = estimate_ram_bytes(file_size_bytes, size_class=size_class)
        estimated_vram_bytes = estimate_vram_bytes(file_size_bytes, size_class=size_class)
        metadata = {"source": "gguf_scan"}
        source_files = sorted({_path_key(item) for item in group_list})
        if source_files:
            metadata["source_files"] = ",".join(source_files)
        companion_list = sorted({str(Path(item).expanduser().resolve()) for item in companion_paths if str(item).strip()})
        if companion_list:
            metadata["mmproj_paths"] = ",".join(companion_list)
        return GGUFModelRecord(
            name=_derive_model_name(path),
            local_path=_path_key(path),
            file_size_bytes=file_size_bytes,
            estimated_ram_bytes=estimated_ram_bytes,
            estimated_vram_bytes=estimated_vram_bytes,
            size_class=size_class,
            vision_enabled=bool(companion_list),
            cost_mode="free",
            metadata=metadata,
        )

    @staticmethod
    def _model_to_dict(model: GGUFModelRecord) -> dict[str, Any]:
        data = _serialize_model_record(model)
        data["file_size_human"] = format_bytes(int(data["file_size_bytes"] or 0))
        data["estimated_ram_human"] = format_bytes(int(data["estimated_ram_bytes"] or 0))
        data["estimated_vram_human"] = format_bytes(int(data["estimated_vram_bytes"] or 0))
        data["vision_enabled"] = bool(data.get("vision_enabled")) or bool((data.get("metadata") or {}).get("mmproj_paths"))
        return data

    def _bootstrap_from_configured_directory(self) -> None:
        configured_directories = self._configured_gguf_directories()
        for configured_directory in configured_directories:
            directory_path = Path(configured_directory).expanduser()
            if not directory_path.exists() or not directory_path.is_dir():
                continue
            self.scan_gguf_directory(directory_path, recursive=True)

    def _configured_gguf_directories(self) -> list[str]:
        directories = get_config_value("ai_model_manager", "gguf_directories", default=[])
        if isinstance(directories, (list, tuple)):
            cleaned = [str(item).strip() for item in directories if str(item).strip()]
            if cleaned:
                return cleaned

        legacy_directory = str(get_config_value("ai_model_manager", "gguf_directory", default="") or "").strip()
        if legacy_directory:
            return [legacy_directory]
        return []

    def _purge_non_primary_scan_records(self, matches: list[Path]) -> int:
        purge_paths: set[str] = set()
        for path in matches:
            if _is_mmproj_file(path):
                purge_paths.add(_path_key(path))
                continue
            shard_parts = _shard_parts(path)
            if shard_parts is not None and shard_parts[1] > 1:
                purge_paths.add(_path_key(path))

        if not purge_paths:
            return 0

        items = _load_model_items()
        next_items: list[dict[str, Any]] = []
        removed = 0
        for item in items:
            local_path_value = str(item.get("local_path") or "").strip()
            if not local_path_value:
                next_items.append(item)
                continue
            local_path = _path_key(Path(local_path_value))
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            if local_path in purge_paths and str(metadata.get("source") or "") == "gguf_scan":
                removed += 1
                continue
            next_items.append(item)

        if removed:
            _save_model_items(next_items)
        return removed


def _iter_gguf_files(directory: Path, *, recursive: bool) -> Iterable[Path]:
    candidates = directory.rglob("*") if recursive else directory.glob("*")
    matched = [path for path in candidates if path.is_file() and path.suffix.lower() == ".gguf"]
    for path in sorted(matched, key=lambda item: str(item).lower()):
        yield path


def _derive_model_name(path: Path) -> str:
    stem = path.stem
    shard_parts = _shard_parts(path)
    if shard_parts is not None:
        stem = shard_parts[0]
    lower_stem = stem.lower()
    mmproj_match = re.search(r"(^|[._-])mmproj([._-]|$)", lower_stem)
    if mmproj_match:
        stem = stem[: mmproj_match.start()].rstrip("._-")
    cleaned = stem.replace("_gguf", "").replace(".gguf", "")
    return cleaned.strip() or path.name


def _update_int(updates: dict[str, Any], key: str, current: int | None) -> int | None:
    if key not in updates:
        return current
    return _parse_int(updates.get(key), default=current)


def _update_float(updates: dict[str, Any], key: str, current: float | None) -> float | None:
    if key not in updates:
        return current
    return _parse_float(updates.get(key), default=current)


def _update_bool(updates: dict[str, Any], key: str, current: bool) -> bool:
    if key not in updates:
        return current
    return _parse_bool(updates.get(key), default=current)


def _update_text(updates: dict[str, Any], key: str, current: str) -> str:
    if key not in updates:
        return current
    value = updates.get(key)
    cleaned = "" if value is None else str(value).strip()
    return current if cleaned == "" else cleaned


def _update_metadata(updates: dict[str, Any], key: str, current: dict[str, str]) -> dict[str, str]:
    if key not in updates:
        return current
    value = updates.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _update_size_classes(updates: dict[str, Any], key: str, current: tuple[str, ...]) -> tuple[str, ...]:
    if key not in updates:
        return current
    return _split_size_classes(updates.get(key))


def infer_size_class(name: str, file_size_bytes: int | None = None) -> str:
    if file_size_bytes is None:
        return "unknown"
    gib = 1024 ** 3
    file_size_gb = file_size_bytes / gib
    if file_size_gb < 40:
        return "small"
    if file_size_gb < 85:
        return "medium"
    if file_size_gb < 256:
        return "large"
    return "xlarge"


def estimate_ram_bytes(file_size_bytes: int, *, size_class: str) -> int:
    normalized_size_class = str(size_class or "").strip()
    multiplier = _SIZE_CLASS_RAM_MULTIPLIERS.get(
        normalized_size_class,
        _SIZE_CLASS_RAM_MULTIPLIERS.get(normalized_size_class.upper(), 2.0),
    )
    return int(round(file_size_bytes * multiplier))


def estimate_vram_bytes(file_size_bytes: int, *, size_class: str) -> int:
    normalized_size_class = str(size_class or "").strip()
    multiplier = _SIZE_CLASS_RAM_MULTIPLIERS.get(
        normalized_size_class,
        _SIZE_CLASS_RAM_MULTIPLIERS.get(normalized_size_class.upper(), 2.0),
    ) * 0.75
    return int(round(file_size_bytes * multiplier))


def format_bytes(value: int) -> str:
    size = float(max(0, int(value)))
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units:
        if size < 1000.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1000.0
