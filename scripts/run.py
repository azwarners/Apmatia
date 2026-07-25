from __future__ import annotations

import os

from apmatia.api.http.app import app
from apmatia.core.app_config import load_app_config
from apmatia.core.security.transport import (
    TransportSecurityConfig,
    TransportSecurityError,
    create_server_ssl_context,
    validate_transport_security,
)
from apmatia.modules.persistence.logger import get_logger

logger = get_logger(__name__)


def _ensure_logging_configured() -> None:
    get_logger(__name__)


def _get_server_config() -> tuple[str, int, TransportSecurityConfig]:
    config = load_app_config()
    server_config = config.get("server", {}) if isinstance(config, dict) else {}
    transport_config = TransportSecurityConfig.model_validate(server_config.get("transport_security", {}))

    host = str(
        os.environ.get("APMATIA_SERVER_HOST")
        or os.environ.get("APMATIA_HOST")
        or server_config.get("host")
        or "127.0.0.1"
    ).strip()
    port_raw = os.environ.get("APMATIA_SERVER_PORT") or os.environ.get("APMATIA_PORT") or server_config.get("port") or 8000
    try:
        port = int(port_raw)
    except (TypeError, ValueError) as exc:
        raise TransportSecurityError(
            f"Invalid server.port value {port_raw!r}. Configure server.port as an integer."
        ) from exc

    return host, port, transport_config


def _run_uvicorn(*, host: str, port: int, ssl_certfile: str | None, ssl_keyfile: str | None, ssl_ca_certs: str | None) -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        ssl_ca_certs=ssl_ca_certs,
    )


def main() -> int:
    _ensure_logging_configured()
    host, port, transport_config = _get_server_config()
    validate_transport_security(host=host, config=transport_config)
    ssl_context = create_server_ssl_context(transport_config)

    protocol = "HTTPS" if ssl_context is not None else "HTTP"
    logger.info(
        "Starting Apmatia core on %s:%s with %s and transport policy %s.",
        host,
        port,
        protocol,
        transport_config.policy.value,
    )

    if transport_config.tls.enabled and not ssl_context:
        raise TransportSecurityError("TLS is enabled but the SSL context could not be created.")

    ssl_certfile = str(transport_config.tls.cert_file) if transport_config.tls.enabled and transport_config.tls.cert_file else None
    ssl_keyfile = str(transport_config.tls.key_file) if transport_config.tls.enabled and transport_config.tls.key_file else None
    ssl_ca_certs = str(transport_config.tls.ca_file) if transport_config.tls.enabled and transport_config.tls.ca_file else None

    _run_uvicorn(
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        ssl_ca_certs=ssl_ca_certs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
