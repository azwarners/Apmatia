from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from apmatia.modules.ai_model_executor import (
    HostResourceSnapshot,
    inspect_host_resources,
    start_model,
    stop_model,
)
from apmatia.modules.ai_model_manager import AIModelManager, GGUFModelRecord


def _manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AIModelManager:
    monkeypatch.setenv("APMATIA_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / "home"))
    return AIModelManager()


def test_host_resource_snapshot_can_be_mocked(monkeypatch):
    from apmatia.modules.ai_model_executor import services

    monkeypatch.setattr(services, "_inspect_system_ram", lambda: (16 * 1024**3, 12 * 1024**3))
    monkeypatch.setattr(services, "_inspect_vram", lambda: (8 * 1024**3, 6 * 1024**3, 1, {"available": True}))

    resources = inspect_host_resources()

    assert resources.ram_total_bytes == 16 * 1024**3
    assert resources.vram_available_bytes == 6 * 1024**3
    assert resources.gpu_count == 1


def test_can_run_and_start_stop_model_with_mocked_processes(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    model = manager.create_model(
        GGUFModelRecord(
            name="Executor Test",
            local_path=str(tmp_path / "models" / "executor-test.gguf"),
            file_size_bytes=1024,
            estimated_ram_bytes=2 * 1024**3,
            estimated_vram_bytes=1024**3,
            size_class="7B",
        )
    )

    from apmatia.modules.ai_model_executor import services

    monkeypatch.setattr(
        services,
        "inspect_host_resources",
        lambda: HostResourceSnapshot(
            ram_total_bytes=16 * 1024**3,
            ram_available_bytes=8 * 1024**3,
            vram_total_bytes=8 * 1024**3,
            vram_available_bytes=4 * 1024**3,
            gpu_count=1,
            source="test",
        ),
    )

    fake_process = MagicMock(pid=4242)
    monkeypatch.setattr(services.subprocess, "Popen", MagicMock(return_value=fake_process))
    killed: list[int] = []
    monkeypatch.setattr(services.os, "kill", lambda pid, _sig: killed.append(pid))

    feasibility = services.can_run_model(model.id)
    assert feasibility["can_run"] is True

    first_start = start_model(model.id, port=9001)
    assert first_start["status"] == "running"
    assert first_start["execution"]["pid"] == 4242
    assert Path(first_start["execution"]["log_path"]).exists()
    assert services.list_execution_records(model_id=model.id)[0].status == "running"

    second_start = start_model(model.id, port=9002)
    assert second_start["stopped_conflicts"]
    assert killed == [4242]

    records = services.list_execution_records(model_id=model.id)
    assert len(records) == 2
    assert any(record.status == "stopped" for record in records)
    assert any(record.status == "running" for record in records)

    stop_result = stop_model(model.id)
    assert stop_result["stopped"] is True
    assert services.list_execution_records(model_id=model.id)[-1].status == "stopped"


def test_can_run_model_reports_insufficient_resources(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    model = manager.create_model(
        GGUFModelRecord(
            name="Too Big",
            local_path=str(tmp_path / "models" / "too-big.gguf"),
            file_size_bytes=1024,
            estimated_ram_bytes=32 * 1024**3,
            estimated_vram_bytes=16 * 1024**3,
            size_class="70B",
        )
    )

    from apmatia.modules.ai_model_executor import services

    monkeypatch.setattr(
        services,
        "inspect_host_resources",
        lambda: HostResourceSnapshot(
            ram_total_bytes=8 * 1024**3,
            ram_available_bytes=4 * 1024**3,
            vram_total_bytes=4 * 1024**3,
            vram_available_bytes=2 * 1024**3,
            gpu_count=1,
            source="test",
        ),
    )

    result = services.can_run_model(model.id)

    assert result["can_run"] is False
    assert "RAM" in " ".join(result["reasons"])


def test_start_model_uses_first_gguf_file_when_model_path_is_directory(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    model_dir = tmp_path / "model-tree"
    nested_dir = model_dir / "subdir"
    nested_dir.mkdir(parents=True)
    first_gguf = model_dir / "alpha-7b.gguf"
    second_gguf = nested_dir / "beta-vision.gguf"
    first_gguf.write_bytes(b"gguf-a")
    second_gguf.write_bytes(b"gguf-b")
    model = manager.create_model(
        GGUFModelRecord(
            name="Directory model",
            local_path=str(model_dir),
            file_size_bytes=0,
            estimated_ram_bytes=1024,
            estimated_vram_bytes=512,
            size_class="7B",
        )
    )

    from apmatia.modules.ai_model_executor import services

    monkeypatch.setattr(
        services,
        "inspect_host_resources",
        lambda: HostResourceSnapshot(
            ram_total_bytes=16 * 1024**3,
            ram_available_bytes=8 * 1024**3,
            vram_total_bytes=8 * 1024**3,
            vram_available_bytes=4 * 1024**3,
            gpu_count=1,
            source="test",
        ),
    )

    captured_command: list[str] = []

    class FakeProcess:
        pid = 9001

    def fake_popen(command, **_kwargs):
        captured_command.extend(command)
        return FakeProcess()

    monkeypatch.setattr(services.subprocess, "Popen", fake_popen)

    result = start_model(model.id, port=9003)

    assert result["status"] == "running"
    assert str(first_gguf.resolve()) in captured_command
    assert str(second_gguf.resolve()) not in captured_command


def test_start_model_uses_first_case_insensitive_gguf_match_when_model_path_is_directory(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    model_dir = tmp_path / "model-tree"
    model_dir.mkdir()
    first_gguf = model_dir / "alpha-7b.GGUF"
    second_gguf = model_dir / "alpha-vision.GGUF"
    first_gguf.write_bytes(b"gguf-a")
    second_gguf.write_bytes(b"gguf-b")
    model = manager.create_model(
        GGUFModelRecord(
            name="Directory model",
            local_path=str(model_dir),
            file_size_bytes=0,
            estimated_ram_bytes=1024,
            estimated_vram_bytes=512,
            size_class="7B",
        )
    )

    from apmatia.modules.ai_model_executor import services

    monkeypatch.setattr(
        services,
        "inspect_host_resources",
        lambda: HostResourceSnapshot(
            ram_total_bytes=16 * 1024**3,
            ram_available_bytes=8 * 1024**3,
            vram_total_bytes=8 * 1024**3,
            vram_available_bytes=4 * 1024**3,
            gpu_count=1,
            source="test",
        ),
    )

    captured_command: list[str] = []

    class FakeProcess:
        pid = 9002

    def fake_popen(command, **_kwargs):
        captured_command.extend(command)
        return FakeProcess()

    monkeypatch.setattr(services.subprocess, "Popen", fake_popen)

    result = start_model(model.id, port=9004)

    assert result["status"] == "running"
    assert str(first_gguf.resolve()) in captured_command
    assert str(second_gguf.resolve()) not in captured_command
