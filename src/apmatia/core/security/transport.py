from __future__ import annotations

import ipaddress
import logging
import os
from datetime import datetime, timezone
import socket
import ssl
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apmatia.core.security.policy import TransportSecurityPolicy, parse_transport_security_policy


logger = logging.getLogger(__name__)


class TransportSecurityError(RuntimeError):
    pass


class TLSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    cert_file: Path | None = None
    key_file: Path | None = None
    ca_file: Path | None = None


class TransportSecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: TransportSecurityPolicy = TransportSecurityPolicy.DEVELOPMENT
    tls: TLSConfig = Field(default_factory=TLSConfig)
    allow_insecure_non_loopback: bool = False
    container_host_loopback_only: bool = False

    @field_validator("policy", mode="before")
    @classmethod
    def _parse_policy(cls, value: object) -> TransportSecurityPolicy:
        return parse_transport_security_policy(value)


def _normalize_host(host: str) -> str:
    candidate = str(host or "").strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1].strip()
    return candidate


def _resolve_host_addresses(host: str) -> set[ipaddress._BaseAddress]:
    addresses: set[ipaddress._BaseAddress] = set()
    for family, _socktype, _proto, _canonname, sockaddr in socket.getaddrinfo(
        host,
        None,
        type=socket.SOCK_STREAM,
    ):
        if not sockaddr:
            continue
        address = sockaddr[0]
        try:
            addresses.add(ipaddress.ip_address(address))
        except ValueError:
            continue
    return addresses


def is_loopback_bind(host: str) -> bool:
    candidate = _normalize_host(host)
    if not candidate:
        return False

    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        pass

    try:
        resolved = _resolve_host_addresses(candidate)
    except socket.gaierror:
        return False

    if not resolved:
        return False

    return all(address.is_loopback for address in resolved)


def _validate_readable_regular_file(path: Path, *, setting_name: str) -> None:
    if not path.exists():
        raise TransportSecurityError(
            f"{setting_name} points to a missing file: {path}. Configure an existing regular file."
        )
    if not path.is_file():
        raise TransportSecurityError(
            f"{setting_name} must point to a regular file: {path}."
        )
    if not os.access(path, os.R_OK):
        raise TransportSecurityError(
            f"{setting_name} is not readable: {path}. Adjust the file permissions or choose another file."
        )


def _validate_tls_files(config: TransportSecurityConfig) -> None:
    cert_file = config.tls.cert_file
    key_file = config.tls.key_file
    if cert_file is None:
        raise TransportSecurityError(
            "TLS is enabled but server.transport_security.tls.cert_file is not set. "
            "Provide a certificate chain file before starting the server."
        )
    if key_file is None:
        raise TransportSecurityError(
            "TLS is enabled but server.transport_security.tls.key_file is not set. "
            "Provide the matching private key file before starting the server."
        )

    _validate_readable_regular_file(cert_file, setting_name="server.transport_security.tls.cert_file")
    _validate_readable_regular_file(key_file, setting_name="server.transport_security.tls.key_file")

    if config.tls.ca_file is not None:
        _validate_readable_regular_file(config.tls.ca_file, setting_name="server.transport_security.tls.ca_file")

    try:
        cert_info = ssl._ssl._test_decode_cert(str(cert_file))
    except Exception as exc:  # pragma: no cover - exercised through startup tests
        raise TransportSecurityError(
            f"server.transport_security.tls.cert_file could not be parsed as a certificate: {cert_file}. "
            "Provide a valid PEM-encoded certificate chain."
        ) from exc

    not_after = cert_info.get("notAfter")
    if not_after:
        try:
            expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)
        except Exception as exc:  # pragma: no cover - defensive
            raise TransportSecurityError(
                f"server.transport_security.tls.cert_file has an unparseable expiration date: {cert_file}."
            ) from exc
        if expires_at <= datetime.now(timezone.utc):
            raise TransportSecurityError(
                f"server.transport_security.tls.cert_file is expired: {cert_file}. "
                "Replace it with a certificate whose validity period has not ended."
            )


def validate_transport_security(*, host: str, config: TransportSecurityConfig) -> None:
    policy = parse_transport_security_policy(config.policy)
    loopback_only = is_loopback_bind(host)
    tls_enabled = bool(config.tls.enabled)

    if policy == TransportSecurityPolicy.DEVELOPMENT:
        if tls_enabled:
            _validate_tls_files(config)
            return
        if loopback_only:
            return
        if config.container_host_loopback_only:
            logger.info(
                "Docker loopback publication mode asserted for non-loopback process bind on host %s. "
                "Apmatia is trusting the operator to publish the container port only on host loopback.",
                host,
            )
            return
        if config.allow_insecure_non_loopback:
            logger.warning(
                "SECURITY WARNING: development policy is allowing plaintext traffic on non-loopback host %s. "
                "This exposes Apmatia traffic over the network and should be used only for deliberate debugging.",
                host,
            )
            return
        raise TransportSecurityError(
            f"Development policy blocks plaintext traffic on non-loopback host {host!r}. "
            "Bind Apmatia to a loopback address such as 127.0.0.1 or ::1, enable TLS, or set "
            "server.transport_security.allow_insecure_non_loopback=true only for temporary debugging."
        )

    if not tls_enabled:
        raise TransportSecurityError(
            f"{policy.value.title()} policy requires TLS for host {host!r}. "
            "Set server.transport_security.tls.enabled=true and provide certificate and key files."
        )

    _validate_tls_files(config)


def create_server_ssl_context(
    config: TransportSecurityConfig,
) -> ssl.SSLContext | None:
    policy = parse_transport_security_policy(config.policy)
    if not config.tls.enabled:
        if policy == TransportSecurityPolicy.DEVELOPMENT:
            return None
        raise TransportSecurityError(
            f"{policy.value.title()} policy requires TLS. "
            "Enable server.transport_security.tls.enabled and configure certificate and key files."
        )

    _validate_tls_files(config)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if hasattr(ssl, "TLSVersion"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2

    if config.tls.ca_file is not None:
        try:
            context.load_verify_locations(cafile=str(config.tls.ca_file))
        except Exception as exc:
            raise TransportSecurityError(
                f"server.transport_security.tls.ca_file could not be loaded: {config.tls.ca_file}."
            ) from exc

    try:
        context.load_cert_chain(
            certfile=str(config.tls.cert_file),
            keyfile=str(config.tls.key_file),
        )
    except Exception as exc:
        raise TransportSecurityError(
            "The configured certificate and private key could not be loaded together. "
            "Check that server.transport_security.tls.cert_file and key_file match and contain valid PEM data."
        ) from exc
    return context
