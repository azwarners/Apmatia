import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from apmatia.modules.discuss.services import (
    get_discussion,
    set_agent_mode,
    prompt_llm,
    TopicManagementBundle,
    DISCUSS_DB,
)
from apmatia.modules.discuss.models import DiscussionTurn
from apmatia.core.models import utc_now
from apmatia.api.internal.agent_management import get_agent
from apmatia.api.internal.agent_prompts import get_agent_system_prompt
from apmatia.api.internal.group_access import is_group_member
from apmatia.api.internal.model_management import get_llm_config
from apmatia.api.internal.users import list_group_members, list_user_groups
from apmatia.modules.ai_model_manager.models import LLMConfig

from .shared import (
    member_group_ids,
    payload_fields_set,
    require_session,
    serialize_discussion,
    serialize_folder,
)

router = APIRouter()


def _json_safe(value, *, _seen: set[int] | None = None):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if _seen is None:
        _seen = set()

    value_id = id(value)
    if value_id in _seen:
        return "<recursive>"

    from dataclasses import is_dataclass, asdict
    from collections.abc import Mapping, Sequence

    if is_dataclass(value):
        _seen.add(value_id)
        return _json_safe(asdict(value, _seen=_seen))

    if isinstance(value, Mapping):
        _seen.add(value_id)
        return {
            str(key): _json_safe(item, _seen=_seen)
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        _seen.add(value_id)
        return [_json_safe(item, _seen=_seen) for item in value]

    if hasattr(value, "model_dump"):
        _seen.add(value_id)
        return _json_safe(value.model_dump(), _seen=_seen)

    if hasattr(value, "dict"):
        _seen.add(value_id)
        try:
            return _json_safe(value.dict(), _seen=_seen)
        except TypeError:
            pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass

    return str(value)


class PromptPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    prompt: str
    agent_id: int | None = None
    discussion_id: str | None = None
    model_id: int | None = None


class GroupPromptPayload(BaseModel):
    prompt: str
    group_id: int
    discussion_id: str | None = None

class DeleteMessagesPayload(BaseModel):
    message_indices: list[int]


class AgentModePayload(BaseModel):
    mode: str


class CreateDiscussionPayload(BaseModel):
    title: str
    group_id: int | None = None
    folder_id: int | None = None
    focused_wiki_id: str | None = None
    agent_id: int | None = None
    participant_agent_ids: list[int] | None = None
    chat_mode: str = "round_robin"
    chat_pause_seconds: float | None = None
    chat_coordinator_agent_id: int | None = None


class UpdateDiscussionPayload(BaseModel):
    title: str | None = None
    group_id: int | None = None
    folder_id: int | None = None
    focused_wiki_id: str | None = None
    participant_agent_ids: list[int] | None = None
    chat_mode: str | None = None
    chat_pause_seconds: float | None = None
    chat_is_paused: bool | None = None
    chat_turn_index: int | None = None
    chat_coordinator_agent_id: int | None = None


class OpenDiscussionPayload(BaseModel):
    discussion_id: str


@router.get("/discussion/state")
def discussion_snapshot(request: Request, discussion_id: str = Query(None)):
    """Get current discussion state. Returns a dict with status info."""
    session = require_session(request)

    messages = []
    turns = []
    if discussion_id and discussion_id.strip():
        try:
            from apmatia.modules.discuss.services import TopicManagementBundle, DISCUSS_DB
            bundle = TopicManagementBundle(DISCUSS_DB)
            turns = bundle.turns.list_by_discussion(discussion_id.strip())
        except Exception:
            turns = []

    # Build messages from turns
    agent_names: dict[int, str] = {}
    for turn in sorted(turns, key=lambda t: (int(t.turn_index) if t.turn_index else 0)):
        role = "user" if str(turn.turn_kind or "").strip().lower() == "user" else "assistant"
        msg = {
            "role": role,
            "text": turn.content or "",
            "speaker_name": "",
            "metadata": turn.metadata or {},
        }
        if turn.speaker_agent_id is not None:
            agent_id = int(turn.speaker_agent_id)
            if agent_id not in agent_names:
                agent = get_agent(agent_id) or {}
                agent_names[agent_id] = str(agent.get("name") or f"Agent {agent_id}")
            msg["speaker_name"] = agent_names[agent_id]
        messages.append(msg)

    return {
        "discussion_id": discussion_id or "",
        "is_streaming": False,
        "messages": messages,
        "activity": None,
        "agent_mode": "discussion",
        "chat_mode": "round_robin",
        "status": "active",
    }


@router.post("/discussions/open")
def open_discussion_entry(request: Request, payload: OpenDiscussionPayload):
    """Open a discussion for the selected contact."""
    session = require_session(request)
    discussion_id = payload.discussion_id
    return {"status": "opened", "discussion_id": discussion_id}


@router.post("/discussion/prompt")
def discussion_prompt(request: Request, payload: PromptPayload):
    session = require_session(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    discussion_id = payload.discussion_id
    agent_id = payload.agent_id
    model_id = payload.model_id
    
    # Debug: Log model info if available
    if os.getenv("APMATIA_DEBUG_BACKEND", "0") == "1":
        print(f"[discussion_prompt] agent_id={agent_id}")
        print(f"[discussion_prompt] model_id={model_id}")
        print(f"[discussion_prompt] discussion_id={discussion_id}")

    llm_config: LLMConfig | None = None
    agent_system_prompt = ""
    agent_name = "Assistant"
    if agent_id is not None:
        agent = get_agent(int(agent_id))
        if agent is not None:
            # Use model_id from payload if provided, otherwise fall back to agent's model
            if model_id is None:
                model_id = agent.get("active_model_id") or agent.get("default_model_id")
                if os.getenv("APMATIA_DEBUG_BACKEND", "0") == "1":
                    print(f"[discussion_prompt] Using agent model_id={model_id}")
            if model_id is not None:
                config_data = get_llm_config(int(model_id))
                if config_data is not None:
                    if os.getenv("APMATIA_DEBUG_BACKEND", "0") == "1":
                        print(f"[discussion_prompt] Model config for id={model_id}:")
                        print(f"[discussion_prompt]   name={config_data.get('name')}")
                        print(f"[discussion_prompt]   model_url={config_data.get('model_url')}")
                        print(f"[discussion_prompt]   backend={config_data.get('backend')}")
                    llm_config = LLMConfig(
                        user_alias=str(config_data.get("user_alias") or ""),
                        backend=str(config_data.get("backend") or "openai_compatible"),
                        provider_name=str(config_data.get("provider_name") or ""),
                        model_url=str(config_data.get("model_url") or ""),
                        api_key=str(config_data.get("api_key") or ""),
                        max_response_size=int(config_data.get("max_response_size") or 8192),
                    )
            agent_name = str(agent.get("name") or "Assistant")
            try:
                agent_system_prompt = get_agent_system_prompt(int(agent_id))
            except Exception:
                agent_system_prompt = ""

    # Build context from system prompt and conversation history
    context_parts = []
    chat_messages: list[dict[str, str]] = []
    if agent_system_prompt.strip():
        context_parts.append(agent_system_prompt)
        chat_messages.append({"role": "system", "content": agent_system_prompt.strip()})
    if discussion_id and discussion_id.strip():
        try:
            bundle = TopicManagementBundle(DISCUSS_DB)
            turns = sorted(
                bundle.turns.list_by_discussion(discussion_id.strip()),
                key=lambda t: t.turn_index,
            )
            # Include last 10 turns as conversation memory
            memory_turns = turns[-10:] if len(turns) > 10 else turns
            history_lines = []
            for t in memory_turns:
                role = "User" if str(t.turn_kind or "").strip().lower() == "user" else agent_name
                content = (t.content or "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")
                    chat_messages.append({
                        "role": "user" if str(t.turn_kind or "").strip().lower() == "user" else "assistant",
                        "content": content,
                    })
            if history_lines:
                context_parts.append("\n".join(history_lines))

        except Exception:
            pass

    context = "\n\n".join(context_parts) if context_parts else None

    # Persist the user's message before invoking a model.  Model calls can be
    # slow or fail, but the conversation should never appear to swallow input.
    turn_bundle = None
    user_turn_index = None
    if discussion_id and discussion_id.strip():
        try:
            from apmatia.modules.discuss.models import DiscussionTurn
            from apmatia.core.models import utc_now

            turn_bundle = TopicManagementBundle(DISCUSS_DB)
            existing_turns = turn_bundle.turns.list_by_discussion(discussion_id.strip())
            user_turn_index = max((t.turn_index for t in existing_turns), default=-1) + 1
            turn_bundle.turns.create(DiscussionTurn(
                topic_id=None,
                discussion_id=discussion_id.strip(),
                speaker_agent_id=None,
                turn_index=user_turn_index,
                turn_kind="user",
                content=prompt,
                metadata={},
                created_at=utc_now(),
            ))
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Unable to save message: {error}") from error

    try:
        chat_messages.append({"role": "user", "content": prompt})
        result = prompt_llm(
            prompt=prompt,
            output_dir="/tmp/apmatia_logs",
            llm_config=llm_config,
            context=context,
            request_metadata={
                "conversation_mode": "direct",
                "chat_messages": chat_messages,
            },
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    # Strip context from the beginning of the result if present
    # The LLM may echo back the full prompt, so we need to extract just the assistant's response
    assistant_response = result
    if context and context.strip() and result.startswith(context.strip()):
        assistant_response = result[len(context.strip()):].strip()

    # Remove leading whitespace/newlines
    if assistant_response:
        assistant_response = assistant_response.lstrip("\n\r\t ").strip()

    # Remove all <think>...</think> blocks
    if assistant_response:
        import re
        assistant_response = re.sub(r'</think>', '', assistant_response, flags=re.DOTALL).strip()
        assistant_response = re.sub(r'<think>.*?</think>', '', assistant_response, flags=re.DOTALL).strip()
        assistant_response = re.sub(r'<think>', '', assistant_response, flags=re.DOTALL).strip()
        assistant_response = assistant_response.strip()

    # Find the first "User:" in the response and take everything before it
    # This handles cases where the LLM echoes the conversation history
    if assistant_response:
        first_user_idx = assistant_response.find("User:")
        if first_user_idx > 0:
            assistant_response = assistant_response[:first_user_idx].strip()
        elif first_user_idx == 0:
            # Response starts with "User:" - just return empty
            assistant_response = ""

    # Final cleanup - remove trailing "Assistant:" if present
    if assistant_response and assistant_response.rstrip().endswith("Assistant:"):
        assistant_response = assistant_response.rstrip()[:-len("Assistant:")].strip()

    # Final trim
    assistant_response = assistant_response.strip()

    # Save the assistant turn after the model responds.  The user turn was
    # intentionally saved before model execution above.
    if turn_bundle is not None and user_turn_index is not None:
        try:
            from apmatia.modules.discuss.models import DiscussionTurn
            from apmatia.core.models import utc_now

            assistant_turn = DiscussionTurn(
                topic_id=None,
                discussion_id=discussion_id.strip(),
                speaker_agent_id=int(agent_id) if agent_id is not None else None,
                turn_index=user_turn_index + 1,
                turn_kind="assistant",
                content=assistant_response,
                metadata={},
                created_at=utc_now(),
            )
            turn_bundle.turns.create(assistant_turn)
        except Exception:
            # Don't fail the prompt if turn saving fails
            pass

    return {"status": "started", "result": str(result)}


@router.post("/discussion/group-prompt")
def group_discussion_prompt(request: Request, payload: GroupPromptPayload):
    """Run one round of a group discussion using each agent's own model."""
    session = require_session(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if not is_group_member(list_user_groups(session.user_id), payload.group_id):
        raise HTTPException(status_code=403, detail="Group access denied.")

    agent_ids: list[int] = []
    for membership in list_group_members(payload.group_id):
        member_kind = getattr(membership, "member_kind", "")
        member_kind = getattr(member_kind, "value", member_kind)
        if str(member_kind).strip().lower() != "agent":
            continue
        if not bool(getattr(membership, "is_enabled", False)):
            continue
        agent_id = getattr(membership, "agent_id", None)
        if agent_id is not None and int(agent_id) not in agent_ids:
            agent_ids.append(int(agent_id))

    if not agent_ids:
        raise HTTPException(status_code=400, detail="The group has no enabled agent members.")

    bundle = TopicManagementBundle(DISCUSS_DB)
    discussion_id = payload.discussion_id.strip() if payload.discussion_id else ""
    existing_turns = (
        sorted(bundle.turns.list_by_discussion(discussion_id), key=lambda turn: turn.turn_index)
        if discussion_id
        else []
    )
    next_index = max((turn.turn_index for turn in existing_turns), default=-1) + 1
    user_name = str(getattr(session, "username", None) or "User")
    history: list[str] = []
    for turn in existing_turns[-10:]:
        content = str(turn.content or "").strip()
        if not content:
            continue
        if str(turn.turn_kind).lower() == "user":
            speaker_name = user_name
        else:
            metadata = turn.metadata if isinstance(turn.metadata, dict) else {}
            speaker_name = str(metadata.get("speaker_name") or "Agent")
            if speaker_name == "Agent" and turn.speaker_agent_id is not None:
                speaker = get_agent(int(turn.speaker_agent_id)) or {}
                speaker_name = str(speaker.get("name") or f"Agent {turn.speaker_agent_id}")
        history.append(f"{speaker_name}: {content}")
    context_lines = history

    if discussion_id:
        bundle.turns.create(DiscussionTurn(
            topic_id=None,
            discussion_id=discussion_id,
            turn_index=next_index,
            turn_kind="user",
            content=prompt,
            metadata={"group_id": payload.group_id},
            created_at=utc_now(),
        ))
        next_index += 1

    results: list[dict[str, object]] = []
    agent_records: list[tuple[int, dict[str, object], str]] = []
    for agent_id in agent_ids:
        agent = get_agent(agent_id) or {}
        agent_name = str(agent.get("name") or f"Agent {agent_id}")
        agent_records.append((agent_id, agent, agent_name))
    roster = ", ".join(agent_name for _, _, agent_name in agent_records)

    for agent_id, agent, agent_name in agent_records:
        model_id = agent.get("active_model_id") or agent.get("default_model_id")
        config_data = get_llm_config(int(model_id)) if model_id is not None else None
        llm_config = None
        if config_data is not None:
            llm_config = LLMConfig(
                user_alias=str(config_data.get("user_alias") or ""),
                backend=str(config_data.get("backend") or "openai_compatible"),
                provider_name=str(config_data.get("provider_name") or ""),
                model_url=str(config_data.get("model_url") or ""),
                api_key=str(config_data.get("api_key") or ""),
                max_response_size=int(config_data.get("max_response_size") or 8192),
            )

        context = "\n".join(context_lines) if context_lines else None
        group_chat_messages: list[dict[str, str]] = [{
            "role": "system",
            "content": (
                f"You are {agent_name}. Respond only as {agent_name}. "
                f"The other participants are: {roster}. "
                "You can see their replies in this discussion. "
                "Never write dialogue on behalf of Nick or another agent."
            ),
        }]
        for turn in existing_turns[-10:]:
            content = str(turn.content or "").strip()
            if not content:
                continue
            if str(turn.turn_kind).lower() == "user":
                group_chat_messages.append({"role": "user", "content": content})
            else:
                metadata = turn.metadata if isinstance(turn.metadata, dict) else {}
                prior_speaker = str(metadata.get("speaker_name") or "Agent").strip()
                group_chat_messages.append({
                    "role": "assistant",
                    "content": f"{prior_speaker}: {content}",
                })
        group_chat_messages.append({"role": "user", "content": prompt})
        for prior_result in results:
            group_chat_messages.append({
                "role": "assistant",
                "content": f"{prior_result['agent_name']}: {prior_result['result']}",
            })
        group_chat_messages.append({
            "role": "user",
            "content": f"Respond as {agent_name} to Nick's message. Respond only for yourself.",
        })
        try:
            result = str(prompt_llm(
                prompt=prompt,
                output_dir="/tmp/apmatia_logs",
                llm_config=llm_config,
                context=context,
                request_metadata={
                    "conversation_mode": "group",
                    "speaker_name": agent_name,
                    "user_name": user_name,
                    "chat_messages": group_chat_messages,
                },
            ))
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

        results.append({"agent_id": agent_id, "agent_name": agent_name, "result": result})
        context_lines.append(f"{agent_name}: {result}")
        if discussion_id:
            bundle.turns.create(DiscussionTurn(
                topic_id=None,
                discussion_id=discussion_id,
                speaker_agent_id=agent_id,
                selected_model_id=int(model_id) if model_id is not None else None,
                turn_index=next_index,
                turn_kind="assistant",
                content=result,
                metadata={"group_id": payload.group_id, "speaker_name": agent_name},
                created_at=utc_now(),
            ))
            next_index += 1

    return {"status": "started", "results": results}


@router.post("/discussion/agent-mode")
def set_discussion_agent_mode(request: Request, payload: AgentModePayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)

    try:
        result = set_agent_mode(
            discussion_id=session.current_discussion_id,
            mode=payload.mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"status": "updated", "result": result}


@router.post("/discussions/open")
def open_discussion_entry(request: Request, payload: OpenDiscussionPayload):
    """Open a discussion for the selected contact."""
    session = require_session(request)
    discussion_id = payload.discussion_id
    return {"status": "opened", "discussion_id": discussion_id}


@router.get("/discussions/tree")
def discussions_tree(request: Request):
    """Return the discussions tree (folders + discussions)."""
    session = require_session(request)
    return {
        "current_discussion_id": None,
        "folders": [],
        "discussions": [],
    }


@router.post("/discussions")
def create_discussion_entry(request: Request, payload: CreateDiscussionPayload):
    session = require_session(request)
    if payload.group_id is not None and not is_group_member(
        list_user_groups(session.user_id),
        payload.group_id,
    ):
        raise HTTPException(status_code=403, detail="Group access denied.")

    # Keep every direct and group conversation isolated.  The old placeholder
    # derived the ID only from the user ID, so creating a group discussion
    # reused that user's existing direct discussion.
    discussion_id = f"disc-{session.user_id}-{uuid4().hex}"
    return {
        "status": "created",
        "discussion": {
            "discussion_id": discussion_id,
            "title": payload.title,
            "agent_mode": "discussion",
            "chat_mode": payload.chat_mode,
            "status": "active",
        },
    }


@router.patch("/discussions/{discussion_id}")
def update_discussion_entry(request: Request, discussion_id: str, payload: UpdateDiscussionPayload):
    session = require_session(request)
    provided_fields = payload_fields_set(payload)
    updates: dict = {}
    if "title" in provided_fields:
        updates["title"] = payload.title
    if "group_id" in provided_fields:
        updates["group_id"] = payload.group_id
    if "folder_id" in provided_fields:
        updates["folder_id"] = payload.folder_id
    if "focused_wiki_id" in provided_fields:
        updates["focused_wiki_id"] = payload.focused_wiki_id
    if "participant_agent_ids" in provided_fields:
        updates["participant_agent_ids"] = payload.participant_agent_ids
    if "chat_mode" in provided_fields:
        updates["chat_mode"] = payload.chat_mode
    if "chat_pause_seconds" in provided_fields:
        updates["chat_pause_seconds"] = payload.chat_pause_seconds
    if "chat_is_paused" in provided_fields:
        updates["chat_is_paused"] = payload.chat_is_paused
    if "chat_turn_index" in provided_fields:
        updates["chat_turn_index"] = payload.chat_turn_index
    if "chat_coordinator_agent_id" in provided_fields:
        updates["chat_coordinator_agent_id"] = payload.chat_coordinator_agent_id
    if not updates:
        raise HTTPException(status_code=400, detail="No discussion updates provided.")

    if "group_id" in updates and updates["group_id"] is not None and not is_group_member(
        list_user_groups(session.user_id),
        updates["group_id"],
    ):
        raise HTTPException(status_code=403, detail="Group access denied.")

    # Placeholder: update discussion in module
    return {
        "status": "updated",
        "discussion": {
            "id": discussion_id,
            **updates,
        },
    }


@router.delete("/discussions/{discussion_id}/messages/{message_index}")
def delete_discussion_message(
    request: Request,
    discussion_id: str,
    message_index: int,
):
    """Delete a single message (turn) from a discussion.

    Deletes the user and assistant turns at the given index pair.
    """
    session = require_session(request)

    try:
        from dataclasses import replace as dc_replace
        from apmatia.modules.discuss.services import (
            TopicManagementBundle,
            DISCUSS_DB,
        )

        bundle = TopicManagementBundle(DISCUSS_DB)
        all_turns = bundle.turns.list_by_discussion(discussion_id)

        # Sort turns by index
        sorted_turns = sorted(all_turns, key=lambda t: t.turn_index)

        # Each message index corresponds to a pair of turns (user + assistant)
        # Find the turn at this message index
        # Message index 0 = turns at indices 0,1; index 1 = turns at indices 2,3, etc.
        start_turn_idx = message_index * 2
        turns_to_delete = []
        for t in sorted_turns:
            if t.turn_index is not None and start_turn_idx <= t.turn_index < start_turn_idx + 2:
                turns_to_delete.append(t)

        if not turns_to_delete:
            raise HTTPException(status_code=404, detail="Message not found.")

        for turn in turns_to_delete:
            bundle.turns.delete(turn.id)

        # Re-index remaining turns
        remaining_turns = bundle.turns.list_by_discussion(discussion_id)
        remaining_turns = sorted(remaining_turns, key=lambda t: t.turn_index)
        for new_idx, turn in enumerate(remaining_turns):
            turn = dc_replace(turn, turn_index=new_idx)
            bundle.turns.update(turn)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {"status": "deleted"}


@router.delete("/discussions/{discussion_id}/messages")
def delete_discussion_messages(
    request: Request,
    discussion_id: str,
    payload: DeleteMessagesPayload,
):
    """Delete multiple messages (turn pairs) from a discussion."""
    session = require_session(request)
    message_indices = payload.message_indices

    if not message_indices:
        raise HTTPException(status_code=400, detail="No message indices provided.")

    try:
        from dataclasses import replace as dc_replace
        from apmatia.modules.discuss.services import (
            TopicManagementBundle,
            DISCUSS_DB,
        )

        bundle = TopicManagementBundle(DISCUSS_DB)
        all_turns = bundle.turns.list_by_discussion(discussion_id)
        sorted_turns = sorted(all_turns, key=lambda t: t.turn_index)

        # Build set of turn indices to delete
        indices_to_delete = set()
        for message_idx in message_indices:
            start_turn_idx = message_idx * 2
            for offset in range(2):
                for t in sorted_turns:
                    if t.turn_index == start_turn_idx + offset:
                        indices_to_delete.add(t.turn_index)

        if not indices_to_delete:
            raise HTTPException(status_code=404, detail="Messages not found.")

        # Delete turns
        for t in sorted_turns:
            if t.turn_index in indices_to_delete:
                bundle.turns.delete(t.id)

        # Re-index remaining turns
        remaining_turns = bundle.turns.list_by_discussion(discussion_id)
        remaining_turns = sorted(remaining_turns, key=lambda t: t.turn_index)
        for new_idx, turn in enumerate(remaining_turns):
            turn = dc_replace(turn, turn_index=new_idx)
            bundle.turns.update(turn)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {"status": "deleted"}
