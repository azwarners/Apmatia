from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from apmatia.core.module_view_runtime import ModuleViewContext


def _service_module():
    import apmatia.modules.apmatia_ai_host_management.services as services

    return importlib.reload(services)


def test_ai_host_crud_round_trip(monkeypatch):
    services = _service_module()
    store: dict[tuple[str, ...], object] = {}

    monkeypatch.setattr(services, "get_config_value", lambda *key, default=None: store.get(tuple(key), default))
    monkeypatch.setattr(services, "load_app_config", lambda: {})

    def save_app_config(config):
        store[("ai_host_management", "hosts")] = config["ai_host_management"]["hosts"]

    monkeypatch.setattr(services, "save_app_config", save_app_config)

    service = services.AIHostManagementService()
    created = service.create_host(
        name="Local node",
        hostname="localhost",
        role="inference",
        connection_type="local",
        credential_ref="~/.ssh/id_ed25519",
    )

    assert created.id == 1
    assert created.credential_ref == "~/.ssh/id_ed25519"

    listed = service.list_hosts()
    assert [host.id for host in listed] == [1]
    assert listed[0].name == "Local node"

    updated = service.update_host(1, notes="Primary host")
    assert updated.notes == "Primary host"
    assert updated.enabled is True

    disabled = service.disable_host(1)
    assert disabled.enabled is False
    assert service.get_host(1).enabled is False

    assert service.delete_host(1) is True
    assert service.get_host(1) is None


def test_plaintext_password_fields_are_rejected():
    services = _service_module()

    with pytest.raises(ValueError, match="Plaintext password"):
        services.validate_host_configuration(
            name="Local node",
            hostname="localhost",
            role="inference",
            password="secret",
        )


def test_credential_ref_storage_round_trip(monkeypatch):
    services = _service_module()
    store: dict[tuple[str, ...], object] = {}

    monkeypatch.setattr(services, "get_config_value", lambda *key, default=None: store.get(tuple(key), default))
    monkeypatch.setattr(services, "load_app_config", lambda: {})
    monkeypatch.setattr(
        services,
        "save_app_config",
        lambda config: store.__setitem__(("ai_host_management", "hosts"), config["ai_host_management"]["hosts"]),
    )

    service = services.AIHostManagementService()
    host = service.create_host(
        name="SSH node",
        hostname="10.0.0.5",
        role="inference",
        connection_type="ssh",
        username="nick",
        credential_ref="ssh-agent:workstation",
    )

    assert host.credential_ref == "ssh-agent:workstation"
    assert service.get_host(host.id).credential_ref == "ssh-agent:workstation"


def test_local_ram_inspection_parses_meminfo(monkeypatch):
    services = _service_module()

    sample_meminfo = (
        "MemTotal:       16384 kB\n"
        "MemAvailable:    4096 kB\n"
        "SwapTotal:       2048 kB\n"
        "SwapFree:        1024 kB\n"
    )

    def fake_read_text(self, encoding="utf-8"):
        if str(self) == "/proc/meminfo":
            return sample_meminfo
        raise FileNotFoundError

    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == "/proc/meminfo")
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    monkeypatch.setattr(services, "_detect_nvidia_gpus", lambda: [])
    monkeypatch.setattr(services, "_detect_sysfs_gpus", lambda: [])

    snapshot = services.inspect_local_resources()

    assert snapshot.total_ram_bytes == 16384 * 1024
    assert snapshot.available_ram_bytes == 4096 * 1024
    assert snapshot.swap_total_bytes == 2048 * 1024
    assert snapshot.swap_free_bytes == 1024 * 1024
    assert snapshot.detected_gpus == []
    assert snapshot.collection_timestamp is not None


def test_gpu_inspection_graceful_fallback(monkeypatch):
    services = _service_module()
    monkeypatch.setattr(services, "_detect_nvidia_gpus", lambda: [])
    monkeypatch.setattr(services, "_detect_sysfs_gpus", lambda: [])
    monkeypatch.setattr(services, "_read_meminfo", lambda: {})

    snapshot = services.inspect_local_resources()

    assert snapshot.detected_gpus == []
    assert snapshot.vram_total_bytes is None
    assert snapshot.vram_free_bytes is None


def test_sysfs_gpu_detection_reads_amd_vram_from_standard_files(tmp_path, monkeypatch):
    services = _service_module()
    drm_root = tmp_path / "class" / "drm"
    card_dir = drm_root / "card0"
    device_dir = card_dir / "device"
    device_dir.mkdir(parents=True)
    (device_dir / "vendor").write_text("0x1002", encoding="utf-8")
    (device_dir / "device").write_text("0x1234", encoding="utf-8")
    (device_dir / "uevent").write_text("DRIVER=amdgpu\n", encoding="utf-8")
    (device_dir / "mem_info_vram_total").write_text(str(96 * 1024**3), encoding="utf-8")
    (device_dir / "mem_info_vram_used").write_text(str(24 * 1024**3), encoding="utf-8")
    (device_dir / "mem_info_vis_vram_total").write_text(str(96 * 1024**3), encoding="utf-8")
    (device_dir / "mem_info_vis_vram_used").write_text(str(24 * 1024**3), encoding="utf-8")

    original_exists = Path.exists
    original_glob = Path.glob

    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/sys/class/drm" or original_exists(self))
    monkeypatch.setattr(
        Path,
        "glob",
        lambda self, pattern: [card_dir] if str(self) == "/sys/class/drm" and pattern == "card[0-9]*" else list(original_glob(self, pattern)),
    )
    monkeypatch.setattr(services, "_detect_nvidia_gpus", lambda: [])

    gpus = services._detect_sysfs_gpus()

    assert len(gpus) == 1
    assert gpus[0]["vendor_id"] == "0x1002"
    assert gpus[0]["driver"] == "amdgpu"
    assert gpus[0]["vram_total_bytes"] == 96 * 1024**3
    assert gpus[0]["vram_free_bytes"] == 72 * 1024**3
    assert gpus[0]["source"] == "sysfs"


def test_gpu_vram_values_are_aggregated(monkeypatch):
    services = _service_module()
    monkeypatch.setattr(
        services,
        "_detect_nvidia_gpus",
        lambda: [
            {"index": 0, "name": "GPU 0", "vram_total_bytes": 8 * 1024**3, "vram_free_bytes": 6 * 1024**3},
            {"index": 1, "name": "GPU 1", "vram_total_bytes": 16 * 1024**3, "vram_free_bytes": 12 * 1024**3},
        ],
    )
    monkeypatch.setattr(services, "_detect_sysfs_gpus", lambda: [])
    monkeypatch.setattr(services, "_read_meminfo", lambda: {})

    snapshot = services.inspect_local_resources()

    assert snapshot.vram_total_bytes == 24 * 1024**3
    assert snapshot.vram_free_bytes == 18 * 1024**3


def test_registered_host_resource_inspection_collects_per_host_reports(monkeypatch):
    services = _service_module()
    store: dict[tuple[str, ...], object] = {}

    monkeypatch.setattr(services, "get_config_value", lambda *key, default=None: store.get(tuple(key), default))
    monkeypatch.setattr(services, "load_app_config", lambda: {})
    monkeypatch.setattr(
        services,
        "save_app_config",
        lambda config: store.__setitem__(("ai_host_management", "hosts"), config["ai_host_management"]["hosts"]),
    )

    service = services.AIHostManagementService()
    local_host = service.create_host(
        name="Local AI",
        hostname="localhost",
        role="inference",
        connection_type="local",
    )
    ssh_host = service.create_host(
        name="Remote AI",
        hostname="192.168.86.132",
        role="inference",
        connection_type="ssh",
        username="nick",
        credential_ref="~/.ssh/id_ed25519",
    )

    local_snapshot = services.HostResourceSnapshot(
        total_ram_bytes=16 * 1024**3,
        available_ram_bytes=8 * 1024**3,
        swap_total_bytes=2 * 1024**3,
        swap_free_bytes=1 * 1024**3,
        vram_total_bytes=8 * 1024**3,
        vram_free_bytes=6 * 1024**3,
        detected_gpus=[{"index": 0, "name": "RTX 4090"}],
    )
    remote_snapshot = services.HostResourceSnapshot(
        total_ram_bytes=32 * 1024**3,
        available_ram_bytes=24 * 1024**3,
        swap_total_bytes=4 * 1024**3,
        swap_free_bytes=3 * 1024**3,
        vram_total_bytes=24 * 1024**3,
        vram_free_bytes=18 * 1024**3,
        detected_gpus=[{"index": 0, "name": "RTX 6000"}],
    )
monkeypatch.setattr(services, "inspect_local_resources", lambda: local_snapshot)
monkeypatch.setattr(services, "_inspect_ssh_host_resources", lambda host, bootstrap_password=None: (remote_snapshot, None))

reports = services.inspect_ai_host_resources()

assert [report.host_id for report in reports] == [local_host.id, ssh_host.id]
assert reports[0].resource_status == "ok"
assert reports[0].total_ram_bytes == 16 * 1024**3
assert reports[0].detected_gpu_summary == "1 GPU(s): RTX 4090"
assert reports[1].resource_status == "ok"
assert reports[1].vram_total_bytes == 24 * 1024**3
assert reports[1].detected_gpu_summary == "1 GPU(s): RTX 6000")


def test_ssh_resource_probe_parses_remote_output(tmp_path, monkeypatch):
    services = _service_module()
    keyfile = tmp_path / "id_ed25519"
    keyfile.write_text("dummy-key", encoding="utf-8")
    host = services.AIHost(
        id=99,
        name="Remote AI",
        hostname="192.168.86.132",
        role="inference",
        connection_type="ssh",
        username="nick",
        credential_ref=str(keyfile),
    )

    class CompletedProcess:
        returncode = 0
        stdout = (
            "MemTotal:       32768 kB\n"
            "MemAvailable:   16384 kB\n"
            "SwapTotal:      4096 kB\n"
            "SwapFree:       3072 kB\n"
            "__APMATIA_GPU_START__\n"
            "SYSFS|0|card0|0x1002|0x1234|amdgpu|103079215104|25769803776|103079215104|25769803776\n"
        )
        stderr = ""

    captured: dict[str, list[str]] = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = list(command)
        return CompletedProcess()

    monkeypatch.setattr(services.subprocess, "run", fake_run)
    monkeypatch.setattr(services, "_resolve_ssh_binary_path", lambda: "/bin/ssh")

    snapshot, error = services._inspect_ssh_host_resources(host)

    assert error is None
    assert snapshot is not None
    assert snapshot.total_ram_bytes == 32768 * 1024
    assert snapshot.available_ram_bytes == 16384 * 1024
    assert snapshot.vram_total_bytes == 96 * 1024**3
    assert snapshot.vram_free_bytes == 72 * 1024**3
    assert captured["command"][0] == "/bin/ssh"
    assert "-i" in captured["command"]
    assert str(keyfile) in captured["command"]
    assert "StrictHostKeyChecking=accept-new" in captured["command"]
    assert "UserKnownHostsFile=/tmp/apmatia_known_hosts" in captured["command"]
    assert "IdentitiesOnly=yes" in captured["command"]
    assert any(part.startswith("SYSFS|") for part in CompletedProcess.stdout.splitlines())


def test_ssh_resource_probe_parses_remote_free_output(tmp_path, monkeypatch):
    services = _service_module()
    keyfile = tmp_path / "id_ed25519"
    keyfile.write_text("dummy-key", encoding="utf-8")
    host = services.AIHost(
        id=100,
        name="Remote AI",
        hostname="192.168.86.132",
        role="inference",
        connection_type="ssh",
        username="nick",
        credential_ref=str(keyfile),
    )

    class CompletedProcess:
        returncode = 0
        stdout = (
            "              total        used        free      shared  buff/cache   available\n"
            "Mem:     34359738368 17179869184 8589934592 1073741824 6442450944 12884901888\n"
            "Swap:     4294967296  1073741824 3221225472\n"
            "__APMATIA_GPU_START__\n"
            "SYSFS|0|card0|0x1002|0x1234|amdgpu|103079215104|25769803776|103079215104|25769803776\n"
        )
        stderr = ""

    monkeypatch.setattr(services.subprocess, "run", lambda *args, **kwargs: CompletedProcess())
    monkeypatch.setattr(services, "_resolve_ssh_binary_path", lambda: "/bin/ssh")

    snapshot, error = services._inspect_ssh_host_resources(host)

    assert error is None
    assert snapshot is not None
    assert snapshot.total_ram_bytes == 34359738368
    assert snapshot.available_ram_bytes == 12884901888
    assert snapshot.swap_total_bytes == 4294967296
    assert snapshot.swap_free_bytes == 3221225472
    assert snapshot.vram_total_bytes == 96 * 1024**3
    assert snapshot.vram_free_bytes == 72 * 1024**3


def test_ssh_resource_probe_reports_missing_client(monkeypatch):
    services = _service_module()
    host = services.AIHost(
        id=7,
        name="Remote AI",
        hostname="192.168.86.132",
        role="inference",
        connection_type="ssh",
        username="nick",
    )

    monkeypatch.setattr(services, "_resolve_ssh_binary_path", lambda: None)

    snapshot, error = services._inspect_ssh_host_resources(host)

    assert snapshot is None
    assert error is not None
    assert "SSH client not available on this Apmatia host." in error
    assert "Host target: nick@192.168.86.132" in error
    assert "credential_ref: (empty)" in error
    assert "ssh-agent" in error
    assert "~/.ssh/id_ed25519" in error
    assert "ssh-keygen -t ed25519" in error


def test_prepare_ssh_key_material_creates_keypair(tmp_path, monkeypatch):
    services = _service_module()
    private_key = tmp_path / "apmatia" / "ssh" / "id_ed25519"
    public_key = Path(f"{private_key}.pub")

    result = services.prepare_ssh_key_material(credential_ref=str(private_key))

    assert result["created"] is True
    assert result["credential_ref"] == str(private_key)
    assert result["private_key_path"] == str(private_key)
    assert result["public_key_path"] == str(public_key)
    assert private_key.exists()
    assert public_key.exists()
    assert "BEGIN OPENSSH PRIVATE KEY" in private_key.read_text(encoding="utf-8")
    assert public_key.read_text(encoding="utf-8").startswith("ssh-ed25519 ")


def test_prepare_ssh_key_material_can_bootstrap_with_password(tmp_path, monkeypatch):
    services = _service_module()
    private_key = tmp_path / "apmatia" / "ssh" / "id_ed25519"
    public_key = Path(f"{private_key}.pub")
    called: dict[str, object] = {}

    def fake_bootstrap(*, username, hostname, port, public_key_path, password):
        called.update(
            {
                "username": username,
                "hostname": hostname,
                "port": port,
                "public_key_path": public_key_path,
                "password": password,
            }
        )
        return True, "installed"

    monkeypatch.setattr(services, "_bootstrap_ssh_public_key_with_password", fake_bootstrap)

    result = services.prepare_ssh_key_material(
        credential_ref=str(private_key),
        username="nick",
        hostname="192.168.86.132",
        port=2222,
        bootstrap_password="secret",
    )

    assert result["bootstrap_attempted"] is True
    assert result["bootstrap_succeeded"] is True
    assert result["bootstrap_error"] == ""
    assert result["ssh_public_key_install_command"].startswith("ssh-copy-id -p 2222")
    assert called["username"] == "nick"
    assert called["hostname"] == "192.168.86.132"
    assert called["port"] == 2222
    assert called["public_key_path"] == public_key
    assert called["password"] == "secret"


def test_prepare_ssh_copy_command_builds_copy_instruction():
    services = _service_module()

    result = services.prepare_ssh_copy_command(
        username="nick",
        hostname="192.168.86.132",
        port=22,
        credential_ref="/home/apmatia/.apmatia/ssh/id_ed25519",
    )

    assert result["created"] is False
    assert result["credential_ref"] == "/home/apmatia/.apmatia/ssh/id_ed25519"
    assert result["ssh_public_key_install_command"] == (
        "ssh-copy-id -p 22 -i /home/apmatia/.apmatia/ssh/id_ed25519.pub "
        "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/apmatia_known_hosts "
        "nick@192.168.86.132"
    )
    assert result["ssh_connection_test_command"] == (
        "ssh -vvv -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "
        "-o UserKnownHostsFile=/tmp/apmatia_known_hosts -p 22 nick@192.168.86.132"
    )


def test_resource_view_lists_registered_hosts(monkeypatch):
    import apmatia.modules.apmatia_ai_host_management.module_views as module_views
    import apmatia.modules.apmatia_ai_host_management.views as views
    from apmatia.modules.apmatia_ai_host_management.models import AIHostResourceReport
module_views = importlib.reload(module_views)
views = importlib.reload(views)
monkeypatch.setattr(
    module_views,
    "inspect_ai_host_resources",
    lambda bootstrap_password=None: [
        AIHostResourceReport(
            host_id=1,
            name="AI PC",
            hostname="192.168.86.132",
            role="inference",
            connection_type="ssh",
            username="nick",
            port=22,
            credential_ref="~/.ssh/id_ed25519",
            enabled=True,
            resource_status="ok",
            total_ram_bytes=16 * 1024**3,
            available_ram_bytes=8 * 1024**3,
            swap_total_bytes=2 * 1024**3,
            swap_free_bytes=2 * 1024**3,
            vram_total_bytes=8 * 1024**3,
            vram_free_bytes=6 * 1024**3,
            detected_gpu_count=1,
            detected_gpu_summary="1 GPU(s): RTX 4090",
            detected_gpus=[{"index": 0, "name": "RTX 4090"}],
        )
    ],
)


    provider = module_views.ApmatiaAIHostManagementModuleViewProvider()
    resource_view = next(view for view in views.VIEW_DESCRIPTORS if view.view_id == "apmatia_ai_host_management.resources.view")

    items = provider.list_items(view=resource_view, context=ModuleViewContext())

    assert len(items) == 1
    assert items[0]["host_id"] == 1
    assert items[0]["name"] == "AI PC"
    assert items[0]["hostname"] == "192.168.86.132"
    assert items[0]["credential_ref"] == "~/.ssh/id_ed25519"
    assert items[0]["resource_status"] == "ok"
    assert items[0]["detected_gpu_count"] == 1
    assert items[0]["detected_gpu_summary"] == "1 GPU(s): RTX 4090"
    assert "AI PC" in items[0]["host_summary"]
    assert "RAM:" in items[0]["resource_summary"]
    assert "GPUs:" in items[0]["gpu_summary"]
    assert "Collected:" in items[0]["resource_error"]
    assert items[0]["ssh_public_key_install_command"].startswith("ssh-copy-id \\\n  -p 22 \\")
    assert "UserKnownHostsFile=/tmp/apmatia_known_hosts" in items[0]["ssh_public_key_install_command"]
    assert items[0]["ssh_connection_test_command"].startswith("ssh -vvv \\\n  -i ~/.ssh/id_ed25519 ")
    assert "UserKnownHostsFile=/tmp/apmatia_known_hosts" in items[0]["ssh_connection_test_command"]
    assert items[0]["ssh_resource_probe_command"].startswith("ssh -i ~/.ssh/id_ed25519 \\\n  -p 22 \\")
    assert "nick@192.168.86.132" in items[0]["ssh_resource_probe_command"]
    assert "noninteractive" not in items[0]["troubleshooting_hint"]
    assert "SSH authentication is already working" not in items[0]["troubleshooting_hint"]


def test_module_view_provider_deletes_host(monkeypatch):
    import apmatia.modules.apmatia_ai_host_management.module_views as module_views

    module_views = importlib.reload(module_views)

    deleted_ids: list[int] = []

    class FakeService:
        def delete_host(self, host_id: int) -> bool:
            deleted_ids.append(host_id)
            return True

    provider = module_views.ApmatiaAIHostManagementModuleViewProvider(service=FakeService())
    command = type("Command", (), {"metadata": {"verb": "delete"}})()

    result = provider.execute_command(
        command=command,
        payload={"item_id": 7},
        context=ModuleViewContext(),
    )

    assert deleted_ids == [7]
    assert result == {"status": "deleted", "host_id": 7}


def test_module_view_provider_edit_can_bootstrap_ssh_key(monkeypatch):
    import apmatia.modules.apmatia_ai_host_management.module_views as module_views

    module_views = importlib.reload(module_views)

    class FakeService:
        def update_host(self, host_id: int, **updates):
            assert host_id == 7
            return type(
                "Host",
                (),
                {
                    "id": 7,
                    "name": "Server",
                    "hostname": "192.168.86.33",
                    "role": "inference",
                    "connection_type": "ssh",
                    "username": "nick",
                    "port": 22,
                    "credential_ref": "/home/apmatia/.apmatia/ssh/id_ed25519",
                    "enabled": True,
                    "notes": "",
                    "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                    "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                },
            )()

        def prepare_ssh_key(self, **kwargs):
            return {"bootstrap_attempted": True, "bootstrap_succeeded": True, "bootstrap_error": "", "message": "ok"}

    provider = module_views.ApmatiaAIHostManagementModuleViewProvider(service=FakeService())
    command = type("Command", (), {"metadata": {"verb": "edit"}})()

    result = provider.execute_command(
        command=command,
        payload={"item_id": 7, "bootstrap_password": "secret"},
        context=ModuleViewContext(),
    )

    assert result["bootstrap_attempted"] is True
    assert result["bootstrap_succeeded"] is True
    assert result["message"] == "ok"


def test_resource_view_reports_probe_command_and_clearer_hint(monkeypatch):
    import apmatia.modules.apmatia_ai_host_management.module_views as module_views

    module_views = importlib.reload(module_views)

    report = type(
        "Report",
        (),
        {
            "host_id": 1,
            "name": "AI PC",
            "hostname": "192.168.86.132",
            "role": "inference",
            "connection_type": "ssh",
            "username": "nick",
            "port": 22,
            "credential_ref": "/home/apmatia/.apmatia/ssh/id_ed25519",
            "enabled": True,
            "resource_status": "unavailable",
            "resource_error": "Remote error: No user exists for uid 1000",
            "collection_timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "total_ram_bytes": 0,
            "available_ram_bytes": 0,
            "swap_total_bytes": 0,
            "swap_free_bytes": 0,
            "vram_total_bytes": None,
            "vram_free_bytes": None,
            "detected_gpu_count": 0,
            "detected_gpu_summary": "",
            "detected_gpus": [],
        },
    )()

    assert "SSH authentication is already working" in module_views._format_troubleshooting_hint(report)
    assert "ssh -i /home/apmatia/.apmatia/ssh/id_ed25519 \\" in module_views._format_ssh_resource_probe_command(report)
    assert "nick@192.168.86.132" in module_views._format_ssh_resource_probe_command(report)


def test_ssh_probe_failure_mentions_authentication_issue():
    services = _service_module()

    host = services.AIHost(
        id=1,
        name="AI PC",
        hostname="192.168.86.132",
        role="inference",
        connection_type="ssh",
        username="nick",
        credential_ref="/home/apmatia/.apmatia/ssh/id_ed25519",
    )
    message = services._format_ssh_probe_failure(
        "SSH inspection failed.",
        host=host,
        ssh_target="nick@192.168.86.132",
        auth_note="credential_ref resolved to SSH key path /home/apmatia/.apmatia/ssh/id_ed25519.",
        ssh_binary="/usr/bin/ssh",
        stderr="Permission denied (publickey,password)",
    )

    assert "current private key was not accepted" in message
    assert "run the copy command from inside the same container" in message


def test_resource_view_troubleshooting_mentions_authentication_issue(monkeypatch):
    import apmatia.modules.apmatia_ai_host_management.module_views as module_views

    module_views = importlib.reload(module_views)

    report = type(
        "Report",
        (),
        {
            "resource_error": "Permission denied (publickey,password)",
        },
    )()

    hint = module_views._format_troubleshooting_hint(report)

    assert "SSH key was not accepted" in hint


def test_host_view_exposes_create_action_payload():
    import apmatia.modules.apmatia_ai_host_management.views as views

    views = importlib.reload(views)
    host_view = next(view for view in views.VIEW_DESCRIPTORS if view.view_id == "apmatia_ai_host_management.hosts.view")
    create_action = next(action for action in host_view.metadata["ui"]["view_actions"] if action["intent"] == "create")

    assert create_action["payload"]["command_id"] == "apmatia_ai_host_management.hosts.create"


def test_host_view_exposes_edit_and_delete_actions():
    import apmatia.modules.apmatia_ai_host_management.views as views

    views = importlib.reload(views)
    host_view = next(view for view in views.VIEW_DESCRIPTORS if view.view_id == "apmatia_ai_host_management.hosts.view")

    actions = host_view.metadata["ui"]["item_actions"]
    intents = [action["intent"] for action in actions]

    assert intents == ["edit", "disable", "delete"]
    assert [action["payload"]["command_id"] for action in actions] == [
        "apmatia_ai_host_management.hosts.edit",
        "apmatia_ai_host_management.hosts.disable",
        "apmatia_ai_host_management.hosts.delete",
    ]


def test_host_create_form_explains_container_visible_key_path():
    import apmatia.modules.apmatia_ai_host_management.views as views
    from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view

    views = importlib.reload(views)
    host_view = next(view for view in views.VIEW_DESCRIPTORS if view.view_id == "apmatia_ai_host_management.hosts.view")

    spec = adapt_module_view(host_view, items=[])

    assert spec.create_form is not None
    assert "credential_ref is the private key path" in spec.create_form.description
    credential_field = next(field for field in spec.create_form.fields if field.key == "credential_ref")
    assert "~/.apmatia/ssh/id_ed25519" in credential_field.help_text
    assert "ssh-keygen -t ed25519 -N \"\"" in credential_field.help_text
    bootstrap_field = next(field for field in spec.create_form.fields if field.key == "bootstrap_password")
    assert bootstrap_field.field_type == "password"
    assert "never stores it" in bootstrap_field.help_text
    assert spec.create_form.actions
    assert [action.intent for action in spec.create_form.actions] == [
        "prepare_ssh_key",
        "prepare_ssh_copy_command",
    ]


def test_host_edit_form_allows_one_time_bootstrap_password():
    import apmatia.modules.apmatia_ai_host_management.views as views
    from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view

    views = importlib.reload(views)
    host_view = next(view for view in views.VIEW_DESCRIPTORS if view.view_id == "apmatia_ai_host_management.hosts.view")

    spec = adapt_module_view(host_view, items=[])

    assert spec.edit_form is not None
    bootstrap_field = next(field for field in spec.edit_form.fields if field.key == "bootstrap_password")
    assert bootstrap_field.field_type == "password"
