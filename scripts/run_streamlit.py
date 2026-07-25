from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from apmatia.core.app_config import load_app_config
from apmatia.core.security.transport import (
    TransportSecurityConfig,
    TransportSecurityError,
    create_server_ssl_context,
    validate_transport_security,
)
from apmatia.modules.persistence.logger import get_logger

logger = get_logger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_APP = REPO_ROOT / "src" / "apmatia" / "interfaces" / "streamlit" / "app.py"


def _ensure_logging_configured() -> None:
    get_logger(__name__)


def _get_streamlit_config() -> tuple[str, int, TransportSecurityConfig]:
    config = load_app_config()
    server_config = config.get("server", {}) if isinstance(config, dict) else {}
    transport_config = TransportSecurityConfig.model_validate(server_config.get("transport_security", {}))

    host = str(
        os.environ.get("APMATIA_STREAMLIT_HOST")
        or os.environ.get("APMATIA_SERVER_HOST")
        or os.environ.get("APMATIA_HOST")
        or server_config.get("host")
        or "127.0.0.1"
    ).strip()
    port_raw = os.environ.get("APMATIA_STREAMLIT_PORT") or 8501
    try:
        port = int(port_raw)
    except (TypeError, ValueError) as exc:
        raise TransportSecurityError(
            f"Invalid streamlit port value {port_raw!r}. Configure APMATIA_STREAMLIT_PORT as an integer."
        ) from exc

    return host, port, transport_config


def _run_streamlit(
    *,
    host: str,
    port: int,
    ssl_certfile: str | None,
    ssl_keyfile: str | None,
    extra_args: list[str] | None = None,
) -> None:
    command = [
        "streamlit",
        "run",
        str(STREAMLIT_APP),
        "--server.port",
        str(port),
        "--server.address",
        host,
        "--server.headless",
        "true",
    ]
    if ssl_certfile and ssl_keyfile:
        command.extend(["--server.sslCertFile", ssl_certfile, "--server.sslKeyFile", ssl_keyfile])
    if extra_args:
        command.extend(extra_args)

    subprocess.run(command, check=True)


def main() -> int:
    _ensure_logging_configured()
    host, port, transport_config = _get_streamlit_config()
    validate_transport_security(host=host, config=transport_config)
    ssl_context = create_server_ssl_context(transport_config)

    protocol = "HTTPS" if ssl_context is not None else "HTTP"
    logger.info(
        "Starting Apmatia Streamlit on %s:%s with %s and transport policy %s.",
        host,
        port,
        protocol,
        transport_config.policy.value,
    )

    ssl_certfile = str(transport_config.tls.cert_file) if transport_config.tls.enabled and transport_config.tls.cert_file else None
    ssl_keyfile = str(transport_config.tls.key_file) if transport_config.tls.enabled and transport_config.tls.key_file else None

    _run_streamlit(
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        extra_args=sys.argv[1:],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
