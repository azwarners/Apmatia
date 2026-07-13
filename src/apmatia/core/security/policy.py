from __future__ import annotations

from enum import StrEnum


class TransportSecurityPolicy(StrEnum):
    DEVELOPMENT = "development"
    LAN = "lan"
    INTERNET = "internet"


def parse_transport_security_policy(value: object) -> TransportSecurityPolicy:
    if isinstance(value, TransportSecurityPolicy):
        return value

    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate:
            try:
                return TransportSecurityPolicy(candidate)
            except ValueError as exc:
                allowed = ", ".join(policy.value for policy in TransportSecurityPolicy)
                raise ValueError(f"Unknown transport security policy: {value!r}. Expected one of: {allowed}.") from exc

    allowed = ", ".join(policy.value for policy in TransportSecurityPolicy)
    raise ValueError(f"Transport security policy must be one of: {allowed}.")

