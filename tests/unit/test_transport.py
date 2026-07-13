from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from apmatia.core.security.transport import (
    TLSConfig,
    TransportSecurityConfig,
    TransportSecurityError,
    create_server_ssl_context,
    validate_transport_security,
)


def _make_certificate_pair(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    cert_file = tmp_path / "server.crt"
    key_file = tmp_path / "server.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key_file),
            "-out",
            str(cert_file),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cert_file, key_file


def _tls_config(cert_file: Path | None = None, key_file: Path | None = None, *, enabled: bool = True) -> TLSConfig:
    return TLSConfig(enabled=enabled, cert_file=cert_file, key_file=key_file)


def test_development_policy_allows_loopback_http():
    config = TransportSecurityConfig()

    validate_transport_security(host="127.0.0.1", config=config)
    assert create_server_ssl_context(config) is None


def test_development_policy_allows_loopback_https(tmp_path):
    cert_file, key_file = _make_certificate_pair(tmp_path)
    config = TransportSecurityConfig(tls=_tls_config(cert_file, key_file))

    validate_transport_security(host="127.0.0.1", config=config)
    assert create_server_ssl_context(config) is not None


def test_development_policy_rejects_non_loopback_http_by_default():
    config = TransportSecurityConfig()

    with pytest.raises(TransportSecurityError, match="non-loopback host"):
        validate_transport_security(host="0.0.0.0", config=config)


def test_development_policy_allows_non_loopback_http_for_trusted_container_publication():
    config = TransportSecurityConfig(container_host_loopback_only=True)

    validate_transport_security(host="0.0.0.0", config=config)
    assert create_server_ssl_context(config) is None


def test_development_policy_allows_non_loopback_http_with_override_and_warns(caplog):
    config = TransportSecurityConfig(allow_insecure_non_loopback=True)

    with caplog.at_level("WARNING"):
        validate_transport_security(host="0.0.0.0", config=config)

    assert any("SECURITY WARNING" in message for message in caplog.messages)
    assert create_server_ssl_context(config) is None


def test_development_policy_allows_non_loopback_https_when_valid(tmp_path):
    cert_file, key_file = _make_certificate_pair(tmp_path)
    config = TransportSecurityConfig(tls=_tls_config(cert_file, key_file))

    validate_transport_security(host="0.0.0.0", config=config)
    assert create_server_ssl_context(config) is not None


@pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0"])
def test_lan_policy_rejects_plain_http(host):
    config = TransportSecurityConfig(policy="lan", container_host_loopback_only=True)

    with pytest.raises(TransportSecurityError, match="requires TLS"):
        validate_transport_security(host=host, config=config)


def test_lan_policy_accepts_valid_tls(tmp_path):
    cert_file, key_file = _make_certificate_pair(tmp_path)
    config = TransportSecurityConfig(policy="lan", tls=_tls_config(cert_file, key_file), container_host_loopback_only=True)

    validate_transport_security(host="0.0.0.0", config=config)
    assert create_server_ssl_context(config) is not None


@pytest.mark.parametrize(
    "config_factory, message",
    [
        (lambda cert, key: TransportSecurityConfig(policy="lan", tls=_tls_config(key_file=key)), "cert_file"),
        (lambda cert, key: TransportSecurityConfig(policy="lan", tls=_tls_config(cert_file=cert)), "key_file"),
    ],
)
def test_lan_policy_rejects_missing_tls_paths(tmp_path, config_factory, message):
    cert_file, key_file = _make_certificate_pair(tmp_path)
    config = config_factory(cert_file, key_file)

    with pytest.raises(TransportSecurityError, match=message):
        validate_transport_security(host="0.0.0.0", config=config)


def test_lan_policy_rejects_nonexistent_tls_files(tmp_path):
    cert_file = tmp_path / "missing.crt"
    key_file = tmp_path / "missing.key"
    config = TransportSecurityConfig(
        policy="lan",
        tls=_tls_config(cert_file, key_file),
    )

    with pytest.raises(TransportSecurityError, match="missing file"):
        validate_transport_security(host="0.0.0.0", config=config)


def test_lan_policy_rejects_malformed_certificate(tmp_path):
    cert_file = tmp_path / "server.crt"
    key_file = tmp_path / "server.key"
    cert_file.write_text("not a certificate", encoding="utf-8")
    key_file.write_text("not a key", encoding="utf-8")
    config = TransportSecurityConfig(policy="lan", tls=_tls_config(cert_file, key_file))

    with pytest.raises(TransportSecurityError, match="could not be parsed as a certificate"):
        validate_transport_security(host="0.0.0.0", config=config)


def test_lan_policy_rejects_mismatched_certificate_and_key(tmp_path):
    cert_one, key_one = _make_certificate_pair(tmp_path / "one")
    cert_two, key_two = _make_certificate_pair(tmp_path / "two")
    config = TransportSecurityConfig(policy="lan", tls=_tls_config(cert_one, key_two))

    validate_transport_security(host="0.0.0.0", config=config)

    with pytest.raises(TransportSecurityError):
        create_server_ssl_context(config)


def test_internet_policy_rejects_plain_http():
    config = TransportSecurityConfig(policy="internet", container_host_loopback_only=True)

    with pytest.raises(TransportSecurityError, match="requires TLS"):
        validate_transport_security(host="0.0.0.0", config=config)


def test_internet_policy_accepts_valid_tls(tmp_path):
    cert_file, key_file = _make_certificate_pair(tmp_path)
    config = TransportSecurityConfig(policy="internet", tls=_tls_config(cert_file, key_file), container_host_loopback_only=True)

    validate_transport_security(host="0.0.0.0", config=config)
    assert create_server_ssl_context(config) is not None


def test_internet_policy_rejects_invalid_tls(tmp_path):
    cert_file = tmp_path / "server.crt"
    key_file = tmp_path / "server.key"
    cert_file.write_text("definitely not a cert", encoding="utf-8")
    key_file.write_text("definitely not a key", encoding="utf-8")
    config = TransportSecurityConfig(policy="internet", tls=_tls_config(cert_file, key_file))

    with pytest.raises(TransportSecurityError):
        create_server_ssl_context(config)


def test_core_server_startup_blocks_insecure_lan_bind_before_accepting_connections(monkeypatch):
    import scripts.run as run_script

    monkeypatch.setattr(
        run_script,
        "load_app_config",
        lambda: {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "transport_security": {
                    "policy": "lan",
                    "tls": {"enabled": False, "cert_file": None, "key_file": None, "ca_file": None},
                    "allow_insecure_non_loopback": False,
                    "container_host_loopback_only": True,
                },
            }
        },
    )
    called = []

    def fake_run_uvicorn(**kwargs):
        called.append(kwargs)

    monkeypatch.setattr(run_script, "_run_uvicorn", fake_run_uvicorn)

    with pytest.raises(TransportSecurityError, match="requires TLS"):
        run_script.main()

    assert called == []


def test_core_server_startup_passes_valid_https_configuration_to_uvicorn(monkeypatch, tmp_path):
    import scripts.run as run_script

    cert_file, key_file = _make_certificate_pair(tmp_path)
    monkeypatch.setattr(
        run_script,
        "load_app_config",
        lambda: {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "transport_security": {
                    "policy": "lan",
                    "tls": {
                        "enabled": True,
                        "cert_file": str(cert_file),
                        "key_file": str(key_file),
                        "ca_file": None,
                    },
                    "allow_insecure_non_loopback": False,
                    "container_host_loopback_only": True,
                },
            }
        },
    )
    called = []

    def fake_run_uvicorn(**kwargs):
        called.append(kwargs)

    monkeypatch.setattr(run_script, "_run_uvicorn", fake_run_uvicorn)

    assert run_script.main() == 0
    assert called == [
        {
            "host": "0.0.0.0",
            "port": 8000,
            "ssl_certfile": str(cert_file),
            "ssl_keyfile": str(key_file),
            "ssl_ca_certs": None,
        }
    ]


def test_streamlit_startup_passes_valid_https_configuration_and_sidebar_flag(monkeypatch, tmp_path):
    import scripts.run_streamlit as streamlit_run

    cert_file, key_file = _make_certificate_pair(tmp_path)
    monkeypatch.setattr(
        streamlit_run,
        "load_app_config",
        lambda: {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "transport_security": {
                    "policy": "lan",
                    "tls": {
                        "enabled": True,
                        "cert_file": str(cert_file),
                        "key_file": str(key_file),
                        "ca_file": None,
                    },
                    "allow_insecure_non_loopback": False,
                    "container_host_loopback_only": True,
                },
            }
        },
    )
    calls = []

    def fake_run(command, check):
        calls.append((command, check))

    monkeypatch.setattr(streamlit_run.subprocess, "run", fake_run)
    monkeypatch.setattr(streamlit_run.sys, "argv", ["run_streamlit.py", "--client.showSidebarNavigation", "false"])

    assert streamlit_run.main() == 0
    assert calls == [
        (
            [
                "streamlit",
                "run",
                str(streamlit_run.STREAMLIT_APP),
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0",
                "--server.headless",
                "true",
                "--server.sslCertFile",
                str(cert_file),
                "--server.sslKeyFile",
                str(key_file),
                "--client.showSidebarNavigation",
                "false",
            ],
            True,
        )
    ]
