from fastapi import HTTPException, Request

from apmatia.api.http.routes import ysparr_extension_routes as routes


def _request(authorization: str | None = None) -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
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
