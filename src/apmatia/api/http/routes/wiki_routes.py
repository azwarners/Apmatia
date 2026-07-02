from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from apmatia.api.internal import wiki_management

from .shared import member_group_ids, payload_fields_set, require_session

router = APIRouter()


class CreateWikiPayload(BaseModel):
    title: str
    description: str | None = None
    owner_agent_id: int | None = None
    mode: int = 0o000


class UpdateWikiPayload(BaseModel):
    title: str | None = None
    description: str | None = None
    owner_agent_id: int | None = None
    mode: int | None = None


class CreateNodePayload(BaseModel):
    parent_id: str
    title: str
    body: str | None = None
    sort_order: int | None = None


class UpdateNodePayload(BaseModel):
    title: str | None = None
    body: str | None = None
    sort_order: int | None = None


class MoveNodePayload(BaseModel):
    new_parent_id: str
    new_sort_order: int | None = None


class ReorderNodePayload(BaseModel):
    new_sort_order: int


@router.get("/wikis")
def list_wikis(
    request: Request,
    owner_agent_id: int | None = Query(default=None),
):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    return wiki_management.list_wikis(
        requester_user_id=session.user_id,
        requester_group_ids=group_ids,
        owner_agent_id=owner_agent_id,
    )


@router.post("/wikis")
def create_wiki(request: Request, payload: CreateWikiPayload):
    session = require_session(request)
    try:
        wiki = wiki_management.create_wiki(
            payload.title,
            owner_user_id=session.user_id,
            description=payload.description,
            owner_agent_id=payload.owner_agent_id,
            mode=payload.mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "created", "wiki": wiki}


@router.get("/wikis/{wiki_id}")
def get_wiki(request: Request, wiki_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    wiki = wiki_management.get_wiki(
        wiki_id,
        requester_user_id=session.user_id,
        requester_group_ids=group_ids,
    )
    if wiki is None:
        raise HTTPException(status_code=404, detail="Wiki not found.")
    return wiki


@router.patch("/wikis/{wiki_id}")
def update_wiki(request: Request, wiki_id: str, payload: UpdateWikiPayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    updates: dict = {}
    if "title" in payload_fields_set(payload):
        updates["title"] = payload.title
    if "description" in payload_fields_set(payload):
        updates["description"] = payload.description
    if "owner_agent_id" in payload_fields_set(payload):
        updates["owner_agent_id"] = payload.owner_agent_id
    if "mode" in payload_fields_set(payload):
        updates["mode"] = payload.mode
    if not updates:
        raise HTTPException(status_code=400, detail="No wiki updates provided.")
    try:
        wiki = wiki_management.update_wiki(
            wiki_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
            **updates,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "updated", "wiki": wiki}


@router.delete("/wikis/{wiki_id}")
def delete_wiki(request: Request, wiki_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        deleted = wiki_management.delete_wiki(
            wiki_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "deleted", "deleted": deleted}


@router.get("/wikis/{wiki_id}/tree")
def get_wiki_tree(request: Request, wiki_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        tree = wiki_management.get_tree(
            wiki_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return tree


@router.get("/wikis/{wiki_id}/flatten")
def flatten_wiki_tree(request: Request, wiki_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        flattened = wiki_management.flatten_tree(
            wiki_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return flattened


@router.get("/wikis/{wiki_id}/search")
def search_wiki(request: Request, wiki_id: str, query: str = Query(..., min_length=1)):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        results = wiki_management.search_wiki(
            wiki_id,
            query,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return results


@router.post("/wikis/{wiki_id}/branches")
def create_branch(request: Request, wiki_id: str, payload: CreateNodePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        node = wiki_management.create_branch(
            wiki_id,
            payload.parent_id,
            payload.title,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
            sort_order=payload.sort_order,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "created", "node": node}


@router.post("/wikis/{wiki_id}/leaves")
def create_leaf(request: Request, wiki_id: str, payload: CreateNodePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        node = wiki_management.create_leaf(
            wiki_id,
            payload.parent_id,
            payload.title,
            body=payload.body or "",
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
            sort_order=payload.sort_order,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "created", "node": node}


@router.patch("/wiki-nodes/{node_id}")
def update_wiki_node(request: Request, node_id: str, payload: UpdateNodePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    updates: dict = {}
    if "title" in payload_fields_set(payload):
        updates["title"] = payload.title
    if "body" in payload_fields_set(payload):
        updates["body"] = payload.body
    if "sort_order" in payload_fields_set(payload):
        updates["sort_order"] = payload.sort_order
    if not updates:
        raise HTTPException(status_code=400, detail="No node updates provided.")
    try:
        node = wiki_management.update_node(
            node_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
            **updates,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "updated", "node": node}


@router.post("/wiki-nodes/{node_id}/move")
def move_wiki_node(request: Request, node_id: str, payload: MoveNodePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        node = wiki_management.move_node(
            node_id,
            new_parent_id=payload.new_parent_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
            new_sort_order=payload.new_sort_order,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "moved", "node": node}


@router.post("/wiki-nodes/{node_id}/reorder")
def reorder_wiki_node(request: Request, node_id: str, payload: ReorderNodePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        node = wiki_management.reorder_node(
            node_id,
            new_sort_order=payload.new_sort_order,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "reordered", "node": node}


@router.delete("/wiki-nodes/{node_id}")
def delete_wiki_node(request: Request, node_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        deleted = wiki_management.delete_node(
            node_id,
            requester_user_id=session.user_id,
            requester_group_ids=group_ids,
        )
    except (PermissionError, ValueError) as error:
        status_code = 403 if isinstance(error, PermissionError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {"status": "deleted", "deleted": deleted}
