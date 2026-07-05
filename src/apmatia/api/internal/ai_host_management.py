from __future__ import annotations

from dataclasses import asdict
from typing import Any

from apmatia.modules.apmatia_ai_host_management import (
    AIHostManagementService,
    delete_ai_host as delete_registered_ai_host,
    inspect_ai_host_resources as inspect_registered_ai_host_resources,
    validate_host_configuration,
)


def _service() -> AIHostManagementService:
    return AIHostManagementService()


def list_ai_hosts() -> list[dict[str, Any]]:
    return [asdict(host) | {"created_at": host.created_at.isoformat(), "updated_at": host.updated_at.isoformat()} for host in _service().list_hosts()]


def create_ai_host(**payload: Any) -> dict[str, Any]:
    host = _service().create_host(**payload)
    return asdict(host) | {"created_at": host.created_at.isoformat(), "updated_at": host.updated_at.isoformat()}


def update_ai_host(host_id: int, **updates: Any) -> dict[str, Any]:
    host = _service().update_host(host_id, **updates)
    return asdict(host) | {"created_at": host.created_at.isoformat(), "updated_at": host.updated_at.isoformat()}


def disable_ai_host(host_id: int) -> dict[str, Any]:
    host = _service().disable_host(host_id)
    return asdict(host) | {"created_at": host.created_at.isoformat(), "updated_at": host.updated_at.isoformat()}


def delete_ai_host(host_id: int) -> dict[str, Any]:
    deleted = delete_registered_ai_host(host_id)
    if not deleted:
        raise ValueError(f"AI host not found: {host_id}")
    return {"status": "deleted", "host_id": host_id}


def show_ai_host(host_id: int) -> dict[str, Any]:
    host = _service().get_host(host_id)
    if host is None:
        raise ValueError(f"AI host not found: {host_id}")
    return asdict(host) | {"created_at": host.created_at.isoformat(), "updated_at": host.updated_at.isoformat()}


def inspect_ai_host_resources(bootstrap_password: str | None = None) -> list[dict[str, Any]]:
    effective_password = bootstrap_password if bootstrap_password else None
    reports = []
    for report in inspect_registered_ai_host_resources(bootstrap_password=effective_password):
        payload = asdict(report)
        payload["collection_timestamp"] = report.collection_timestamp.isoformat()
        reports.append(payload)
    return reports


def validate_ai_host(**payload: Any) -> dict[str, Any]:
    return validate_host_configuration(**payload)
