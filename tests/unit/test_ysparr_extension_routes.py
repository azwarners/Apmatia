import hashlib
import hmac
import json

from fastapi import HTTPException, Request

from apmatia.api.http.routes import ysparr_extension_routes as routes


def _request(authorization: str | None = None, *, principal: str | None = None, signature: str | None = None) -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    if principal is not None:
        headers.append((b"x-ysparr-principal", principal.encode()))
    if signature is not None:
        headers.append((b"x-ysparr-principal-signature", signature.encode()))
    return Request({"type": "http", "headers": headers, "method": "GET", "path": "/"})


def _agent() -> dict:
    return {
        "id": 7,
        "name": "Luna",
        "is_public": True,
        "model": {"backend": "openai_compatible"},
        "system_prompt": "Be concise.",
    }


def test_catalog_is_public_and_model_backed(monkeypatch) -> None:
    monkeypatch.delenv(routes.EXTENSION_API_KEY_ENV, raising=False)
    monkeypatch.setattr(routes, "list_agents", lambda: [_agent()])
    monkeypatch.setattr(routes, "_is_publication_eligible", lambda agent: True)
    monkeypatch.setattr(
        routes,
        "_public_agent",
        lambda agent: {
            "id": agent["id"],
            "name": agent["name"],
            "model": agent["model"],
            "system_prompt": agent["system_prompt"],
        },
    )

    assert routes.catalog(_request()) == {
        "version": "1",
        "entries": [
            {
                "id": "Luna",
                "name": "Luna",
                "aliases": ["apmatia-agent-7"],
                "owned_by": "apmatia",
                "target": {"preferred_model_type": "openai_compatible"},
            }
        ],
    }


def test_catalog_requires_configured_bearer_key(monkeypatch) -> None:
    monkeypatch.setenv(routes.EXTENSION_API_KEY_ENV, "secret")

    try:
        routes.catalog(_request("Bearer wrong"))
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("catalog accepted invalid extension credentials")


def test_mapped_principal_sees_owned_private_prompt_agent(monkeypatch) -> None:
    secret = "secret"
    principal = "ys-user-a"
    signature = hmac.new(secret.encode(), principal.encode(), hashlib.sha256).hexdigest()
    monkeypatch.setenv(routes.EXTENSION_API_KEY_ENV, secret)
    monkeypatch.setenv(routes.PRINCIPAL_MAP_ENV, json.dumps({principal: 42}))
    private = {**_agent(), "id": 8, "name": "Private Luna", "is_public": False, "owner_user_id": 42}
    monkeypatch.setattr(routes, "list_agents", lambda: [private])
    monkeypatch.setattr(routes, "_is_publication_eligible", lambda agent: True)
    monkeypatch.setattr(routes, "_public_agent", lambda agent: {**agent, "model": agent["model"]})

    result = routes.catalog(_request("Bearer secret", principal=principal, signature=signature))
    assert result["entries"][0]["id"] == "apmatia-agent-8"
    assert result["entries"][0]["aliases"] == []


def test_unmapped_or_invalid_principal_cannot_resolve_private_agent(monkeypatch) -> None:
    secret = "secret"
    private = {**_agent(), "is_public": False, "owner_user_id": 42}
    monkeypatch.setenv(routes.EXTENSION_API_KEY_ENV, secret)
    monkeypatch.setenv(routes.PRINCIPAL_MAP_ENV, "{}")
    monkeypatch.setattr(routes, "list_agents", lambda: [private])
    monkeypatch.setattr(routes, "_is_publication_eligible", lambda agent: True)

    with __import__("pytest").raises(HTTPException) as error:
        routes.resolve(
            routes.ResolveRequest(version="1", model="apmatia-agent-7"),
            _request("Bearer secret", principal="ys-user-a", signature="bad"),
        )
    assert error.value.status_code == 401


def test_two_mapped_principals_are_isolated_and_public_keys_see_only_public_agents(monkeypatch) -> None:
    secret = "secret"
    principal_a = "ys-user-a"
    principal_b = "ys-user-b"
    signature_a = hmac.new(secret.encode(), principal_a.encode(), hashlib.sha256).hexdigest()
    signature_b = hmac.new(secret.encode(), principal_b.encode(), hashlib.sha256).hexdigest()
    public = {**_agent(), "id": 1, "name": "Public starter", "is_public": True, "owner_user_id": 1}
    private_a = {**_agent(), "id": 8, "name": "Private Luna", "is_public": False, "owner_user_id": 42}
    private_b = {**_agent(), "id": 9, "name": "Private Rowan", "is_public": False, "owner_user_id": 43}
    monkeypatch.setenv(routes.EXTENSION_API_KEY_ENV, secret)
    monkeypatch.setenv(routes.PRINCIPAL_MAP_ENV, json.dumps({principal_a: 42, principal_b: 43}))
    monkeypatch.setattr(routes, "list_agents", lambda: [public, private_a, private_b])
    monkeypatch.setattr(routes, "_is_publication_eligible", lambda agent: True)
    monkeypatch.setattr(
        routes,
        "_public_agent",
        lambda agent: {**agent, "model": agent["model"], "system_prompt": f"Prompt for {agent['name']}"},
    )

    catalog_a = routes.catalog(_request("Bearer secret", principal=principal_a, signature=signature_a))
    catalog_b = routes.catalog(_request("Bearer secret", principal=principal_b, signature=signature_b))
    public_catalog = routes.catalog(_request("Bearer secret"))
    assert {entry["id"] for entry in catalog_a["entries"]} == {"Public starter", "apmatia-agent-8"}
    assert {entry["id"] for entry in catalog_b["entries"]} == {"Public starter", "apmatia-agent-9"}
    assert {entry["id"] for entry in public_catalog["entries"]} == {"Public starter"}

    selected = routes.resolve(
        routes.ResolveRequest(version="1", model="apmatia-agent-8"),
        _request("Bearer secret", principal=principal_a, signature=signature_a),
    )
    assert selected["contributions"] == [{"role": "system", "content": "Prompt for Private Luna"}]
    assert selected["target"] == {"preferred_model_type": "openai_compatible"}

    for principal, signature in ((principal_b, signature_b), (None, None)):
        try:
            routes.resolve(
                routes.ResolveRequest(version="1", model="apmatia-agent-8"),
                _request("Bearer secret", principal=principal, signature=signature),
            )
        except HTTPException as error:
            assert error.status_code == 404
        else:
            raise AssertionError("cross-user or public access resolved a private agent")
