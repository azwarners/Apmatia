"""Apmatia-owned, read-only Ysparr extension contract."""

import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.agent_management import list_agents
from apmatia.api.internal.tools import execute_tool_call, list_tools_available_to_agent
from apmatia.api.http.routes.agent_routes import _is_publication_eligible
from apmatia.api.http.routes.public_agent_routes import _public_agent

from .ysparr_ids import legacy_agent_model_id, named_agent_model_id


router = APIRouter(prefix="/public/ysparr", tags=["ysparr-extension"])
EXTENSION_API_KEY_ENV = "APMATIA_YSPARR_EXTENSION_API_KEY"
PRINCIPAL_MAP_ENV = "APMATIA_YSPARR_PRINCIPAL_MAP"
PRINCIPAL_HEADER = "x-ysparr-principal"
PRINCIPAL_SIGNATURE_HEADER = "x-ysparr-principal-signature"


class ResolveRequest(BaseModel):
    version: str = Field(min_length=1)
    model: str = Field(min_length=1)
    request: dict = Field(default_factory=dict)


class ToolInvocationRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)
    call_id: str | None = None
    approval_granted: bool = False


@router.get("/catalog")
def catalog(request: Request) -> dict:
    _authorize(request)
    principal_user_id = _principal_user_id(request)
    entries = []
    for agent in list_agents():
        if not _is_publication_eligible(agent):
            continue
        is_public = bool(agent.get("is_public", False))
        is_owned = principal_user_id is not None and agent.get("owner_user_id") == principal_user_id
        if not is_public and not is_owned:
            continue
        public = _public_agent(agent)
        model = public.get("model")
        if not isinstance(model, dict) or not model.get("backend"):
            continue
        entries.append({
            "id": named_agent_model_id(public["name"]) if is_public else legacy_agent_model_id(public["id"]),
            "name": public["name"],
            "aliases": [legacy_agent_model_id(public["id"])] if is_public else [],
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
    principal_user_id = _principal_user_id(request)
    agent = _agent_for_entry(entry, list_agents())
    if agent is None or not _is_publication_eligible(agent):
        raise HTTPException(status_code=404, detail="extension entry not found")
    if not agent.get("is_public", False) and agent.get("owner_user_id") != principal_user_id:
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


@router.get("/agents/{agent_id}/tools")
def agent_tools(agent_id: int, request: Request) -> dict:
    """Return assigned Sidecaravan tools for one verified private agent."""
    _authorized_private_agent(request, agent_id)
    tools = [
        tool
        for tool in list_tools_available_to_agent(agent_id)
        if tool.get("metadata", {}).get("integration") == "sidecaravan"
    ]
    return {"version": "1", "agent_id": agent_id, "tools": tools}


@router.post("/agents/{agent_id}/tools/{tool_name}")
def invoke_agent_tool(
    agent_id: int,
    tool_name: str,
    payload: ToolInvocationRequest,
    request: Request,
) -> dict:
    """Invoke an assigned Sidecaravan tool after rechecking the principal mapping."""
    _authorized_private_agent(request, agent_id)
    tool = next(
        (
            item
            for item in list_tools_available_to_agent(agent_id)
            if item.get("name") == tool_name and item.get("metadata", {}).get("integration") == "sidecaravan"
        ),
        None,
    )
    if tool is None or tool.get("id") is None:
        raise HTTPException(status_code=404, detail="agent tool not found")
    return execute_tool_call(
        tool_id=int(tool["id"]),
        arguments=payload.arguments,
        requester_agent_id=agent_id,
        call_id=payload.call_id,
        approval_granted=payload.approval_granted,
    )


def _agent_for_entry(entry: dict, agents: list[dict]) -> dict | None:
    """Resolve a catalog entry to the exact current agent record.

    Private selectors are ID-based so an agent-name collision cannot make a
    request resolve to a different user's agent. Public named selectors retain
    their legacy behavior and are restricted to published records.
    """
    selector = entry.get("id", "")
    if selector.startswith("apmatia-agent-"):
        try:
            agent_id = int(selector.removeprefix("apmatia-agent-"))
        except ValueError:
            return None
        return next((agent for agent in agents if agent.get("id") == agent_id), None)
    return next(
        (agent for agent in agents if agent.get("name") == entry.get("name") and agent.get("is_public", False)),
        None,
    )


def _authorize(request: Request) -> None:
    expected = os.getenv(EXTENSION_API_KEY_ENV)
    if not expected:
        return
    authorization = request.headers.get("authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid extension credentials")


def _principal_user_id(request: Request) -> int | None:
    principal = request.headers.get(PRINCIPAL_HEADER)
    signature = request.headers.get(PRINCIPAL_SIGNATURE_HEADER)
    if not principal and not signature:
        return None
    expected = os.getenv(EXTENSION_API_KEY_ENV)
    if not expected or not principal or not signature:
        raise HTTPException(status_code=401, detail="invalid principal assertion")
    expected_signature = hmac.new(expected.encode(), principal.encode(), "sha256").hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="invalid principal assertion")
    try:
        mapping = json.loads(os.getenv(PRINCIPAL_MAP_ENV, "{}"))
        user_id = mapping.get(principal)
        return int(user_id) if user_id is not None else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _authorized_private_agent(request: Request, agent_id: int) -> dict:
    principal_user_id = _principal_user_id(request)
    if principal_user_id is None:
        raise HTTPException(status_code=404, detail="agent tool not found")
    agent = next((item for item in list_agents() if item.get("id") == agent_id), None)
    if (
        agent is None
        or agent.get("is_public", False)
        or agent.get("owner_user_id") != principal_user_id
    ):
        raise HTTPException(status_code=404, detail="agent tool not found")
    return agent
