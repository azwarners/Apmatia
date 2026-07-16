from __future__ import annotations

from pathlib import Path

import pytest

from apmatia.modules.ai_model_manager import AIModelManager, GGUFModelRecord, TaskSizePreference
from apmatia.modules.ai_model_manager.services import infer_size_class


def _manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AIModelManager:
    config_dir = tmp_path / "config"
    monkeypatch.setenv("APMATIA_CONFIG_DIR", str(config_dir))
    return AIModelManager()


def test_model_crud_round_trips_records(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    created_large = manager.create_model(
        GGUFModelRecord(
            name="Local 7B Large",
            local_path=str(tmp_path / "models" / "local-7b-large.gguf"),
            file_size_bytes=2048,
            estimated_ram_bytes=4096,
            estimated_vram_bytes=3072,
            size_class="7B",
            cost_mode="free",
        )
    )
    created_small = manager.create_model(
        GGUFModelRecord(
            name="Local 7B Small",
            local_path=str(tmp_path / "models" / "local-7b-small.gguf"),
            file_size_bytes=1024,
            estimated_ram_bytes=2048,
            estimated_vram_bytes=1536,
            size_class="7B",
            cost_mode="free",
        )
    )
    updated = manager.update_model(created_small.id, notes="Checked by hand", cost_mode="metered")

    listed = manager.list_models()

    assert len(listed) == 2
    assert listed[0].id == created_small.id
    assert listed[1].id == created_large.id
    assert updated.notes == "Checked by hand"
    assert updated.cost_mode == "metered"
    assert manager.delete_model(created_small.id) is True
    assert manager.delete_model(created_large.id) is True
    assert manager.list_models() == []


def test_scan_gguf_directory_discovers_files_and_preserves_manual_flags(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    gguf_dir = tmp_path / "gguf"
    gguf_dir.mkdir()
    model_file = gguf_dir / "alpha-7b-instruct.gguf"
    model_file.write_bytes(b"gguf-model-bytes")

    first_scan = manager.scan_gguf_directory(gguf_dir)
    model_id = first_scan["items"][0]["id"]

    manager.update_model(
        model_id,
        cost_mode="metered",
        input_token_cost_per_1k=0.0125,
        output_token_cost_per_1k=0.025,
        notes="manually tuned",
    )

    model_file.write_bytes(b"gguf-model-bytes-with-more-data")
    second_scan = manager.scan_gguf_directory(gguf_dir)
    rescanned = manager.get_model(model_id)

    assert first_scan["created"] == 1
    assert first_scan["updated"] == 0
    assert second_scan["created"] == 0
    assert second_scan["updated"] == 1
    assert rescanned is not None
    assert rescanned.cost_mode == "metered"
    assert rescanned.input_token_cost_per_1k == 0.0125
    assert rescanned.output_token_cost_per_1k == 0.025
    assert rescanned.file_size_bytes == model_file.stat().st_size


def test_scan_gguf_directory_collapses_shards_and_attaches_mmproj_companions(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    gguf_dir = tmp_path / "gguf"
    vision_dir = gguf_dir / "vision"
    vision_dir.mkdir(parents=True)

    standalone = gguf_dir / "alpha-7b.gguf"
    ignored_mmproj = gguf_dir / "alpha-mmproj-f16.gguf"
    shard_first = vision_dir / "beta-13b.Q4_K_M-00001-of-00003.gguf"
    shard_second = vision_dir / "beta-13b.Q4_K_M-00002-of-00003.gguf"
    shard_third = vision_dir / "beta-13b.Q4_K_M-00003-of-00003.gguf"
    mmproj = vision_dir / "beta-13b.mmproj-f16.gguf"
    standalone.write_bytes(b"standalone")
    ignored_mmproj.write_bytes(b"ignored")
    shard_first.write_bytes(b"first")
    shard_second.write_bytes(b"second")
    shard_third.write_bytes(b"third")
    mmproj.write_bytes(b"mmproj")

    result = manager.scan_gguf_directory(gguf_dir)
    listed = manager.list_models()

    assert result["discovered"] == 6
    assert result["scanned"] == 2
    assert result["created"] == 2
    assert result["removed"] == 0
    assert len(listed) == 2
    standalone_model = next(model for model in listed if model.local_path == str(standalone.resolve()))
    shard_model = next(model for model in listed if model.local_path == str(shard_first.resolve()))
    assert standalone_model.name == "alpha-7b"
    assert shard_model.name == "beta-13b.Q4_K_M"
    assert shard_model.file_size_bytes == shard_first.stat().st_size + shard_second.stat().st_size + shard_third.stat().st_size
    assert shard_model.metadata["mmproj_paths"] == str(mmproj.resolve())
    assert standalone_model.vision_enabled is False
    assert shard_model.vision_enabled is True
    assert all(item["file_size_human"].endswith("B") for item in result["items"])


def test_scan_gguf_directory_ignores_mmproj_files_named_with_mmproj_marker_and_sorts_by_size(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    gguf_dir = tmp_path / "gguf"
    vision_dir = gguf_dir / "vision"
    vision_dir.mkdir(parents=True)

    small = gguf_dir / "small.gguf"
    ignored = gguf_dir / "small-mmproj-f16.gguf"
    larger = vision_dir / "vision-large.gguf"
    mmproj = vision_dir / "vision.mmproj-f16.gguf"
    small.write_bytes(b"s")
    ignored.write_bytes(b"ignored")
    larger.write_bytes(b"vision-large")
    mmproj.write_bytes(b"mmproj")

    result = manager.scan_gguf_directory(gguf_dir)

    assert result["created"] == 2
    assert [item["name"] for item in result["items"]] == ["small", "vision-large"]
    assert all("mmproj" not in item["name"].lower() for item in result["items"])
    assert manager.list_models()[0].local_path == str(small.resolve())


@pytest.mark.parametrize(
    ("size_gb", "expected"),
    [
        (1, "small"),
        (40, "medium"),
        (84.999, "medium"),
        (85, "large"),
        (255.999, "large"),
        (256, "xlarge"),
    ],
)
def test_infer_size_class_uses_file_size_bands(size_gb, expected):
    gib = 1024 ** 3
    assert infer_size_class("anything", int(size_gb * gib)) == expected


def test_ram_estimate_storage_round_trip(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    created = manager.create_model(
        GGUFModelRecord(
            name="Estimator",
            local_path=str(tmp_path / "estimator.gguf"),
            file_size_bytes=4096,
            estimated_ram_bytes=8192,
            estimated_vram_bytes=4096,
            size_class="small",
        )
    )
    manager.update_model(created.id, estimated_ram_bytes=12288)

    refreshed = manager.get_model(created.id)

    assert refreshed is not None
    assert refreshed.estimated_ram_bytes == 12288


def test_cost_flags_persist(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    created = manager.create_model(
        GGUFModelRecord(
            name="Paid model",
            local_path=str(tmp_path / "paid.gguf"),
            file_size_bytes=8192,
            estimated_ram_bytes=16384,
            estimated_vram_bytes=8192,
            size_class="13B",
            cost_mode="metered",
            input_token_cost_per_1k=0.01,
            output_token_cost_per_1k=0.02,
        )
    )

    refreshed = manager.get_model(created.id)

    assert refreshed is not None
    assert refreshed.cost_mode == "metered"
    assert refreshed.input_token_cost_per_1k == 0.01
    assert refreshed.output_token_cost_per_1k == 0.02


def test_task_preference_configuration_round_trip(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    created = manager.upsert_task_preference(
        TaskSizePreference(
            task_name="coding assistant",
            preferred_size_classes=("7B", "13B"),
            notes="Prefer models with good instruction tuning.",
        )
    )
    manager.update_task_preference(created.id, preferred_size_classes="13B, 32B")

    refreshed = manager.get_task_preference(created.id)

    assert refreshed is not None
    assert refreshed.task_name == "coding assistant"
    assert refreshed.preferred_size_classes == ("13B", "32B")
    assert refreshed.notes == "Prefer models with good instruction tuning."


def test_list_models_bootstraps_from_configured_directory_when_empty(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    gguf_dir = tmp_path / "gguf"
    gguf_dir.mkdir()
    model_file = gguf_dir / "bootstrap.gguf"
    model_file.write_bytes(b"gguf")

    monkeypatch.setattr(
        "apmatia.modules.ai_model_manager.services.get_config_value",
        lambda *keys, default=None: str(gguf_dir) if keys == ("ai_model_manager", "gguf_directory") else default,
    )

    listed = manager.list_models()

    assert len(listed) == 1
    assert listed[0].local_path == str(model_file.resolve())
