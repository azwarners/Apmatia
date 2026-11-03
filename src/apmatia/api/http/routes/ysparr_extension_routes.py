"""Apmatia-owned, read-only Ysparr extension contract."""

import hmac
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.agent_management import list_agents
from apmatia.api.http.routes.agent_routes import _is_publication_eligible
from apmatia.api.http.routes.public_agent_routes import _public_agent

from .ysparr_ids import legacy_agent_model_id, named_agent_model_id


router = APIRouter(prefix="/public/ysparr", tags=["ysparr-extension"])
EXTENSION_API_KEY_ENV = "APMATIA_YSPARR_EXTENSION_API_KEY"


class ResolveRequest(BaseModel):
    version: str = Field(min_length=1)
    model: str = Field(min_length=1)
    request: dict = Field(default_factory=dict)


@router.get("/catalog")
def catalog(request: Request) -> dict:
    _authorize(request)
    entries = []
    for agent in list_agents():
        if not _is_publication_eligible(agent) or not agent.get("is_public", False):
            continue
        public = _public_agent(agent)
        model = public.get("model")
        if not isinstance(model, dict) or not model.get("backend"):
            continue
        entries.append({
            "id": named_agent_model_id(public["name"]),
            "name": public["name"],
            "aliases": [legacy_agent_model_id(public["id"])],
            "owned_by": "apmatia",
            "target": {"preferred_model_type": model["backend"]},
        })
    return {"version": "1", "entries": entries}


@router.post("/resolve")
def resolve(payload: ResolveRequest, request: Request) -> dict:
    _authorize(request)
    if payload.version != "1":
        raise HTTPException(status_code=400, detail="unsupported extension contract")
    entry = next(
        (item for item in catalog(request)["entries"] if payload.model in {item["id"], *item["aliases"]}),
        None,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="extension entry not found")
    agent_name = entry["name"]
    agent = next((item for item in list_agents() if item["name"] == agent_name), None)
    if agent is None or not _is_publication_eligible(agent) or not agent.get("is_public", False):
        raise HTTPException(status_code=404, detail="extension entry not found")
    public = _public_agent(agent)
    model = public.get("model")
    if not isinstance(model, dict) or not model.get("backend"):
        raise HTTPException(status_code=404, detail="extension entry not found")
    return {
        "version": "1",
        "contributions": [{"role": "system", "content": public["system_prompt"]}],
        "target": {"preferred_model_type": model["backend"]},
    }


def _authorize(request: Request) -> None:
    expected = os.getenv(EXTENSION_API_KEY_ENV)
    if not expected:
        return
    authorization = request.headers.get("authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid extension credentials")
