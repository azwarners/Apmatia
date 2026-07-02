from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

GroupChatMode = Literal["single", "round_robin", "auto_paced", "continuous", "direct"]

GROUP_CHAT_MODES: tuple[GroupChatMode, ...] = (
    "single",
    "round_robin",
    "auto_paced",
    "continuous",
    "direct",
)


@dataclass(slots=True, frozen=True)
class GroupChatParticipant:
    agent_id: int
    name: str


@dataclass(slots=True, frozen=True)
class GroupChatTurn:
    speaker_agent_id: int
    speaker_name: str
    turn_prompt: str


@dataclass(slots=True, frozen=True)
class GroupChatPlan:
    mode: GroupChatMode
    turns: list[GroupChatTurn]
    awaits_user: bool
    continue_automatically: bool
    pause_seconds: float | None
    next_turn_index: int
    coordinator_agent_id: int | None = None


def normalize_group_chat_mode(value: object | None) -> GroupChatMode:
    candidate = "single" if value is None else str(value).strip().lower()
    if candidate in GROUP_CHAT_MODES:
        return candidate  # type: ignore[return-value]
    return "single"


def unique_participants(
    participants: Sequence[GroupChatParticipant],
    *,
    preferred_agent_id: int | None = None,
) -> list[GroupChatParticipant]:
    seen: set[int] = set()
    ordered = list(participants)
    if preferred_agent_id is not None:
        ordered = sorted(
            ordered,
            key=lambda participant: 0 if participant.agent_id == preferred_agent_id else 1,
        )

    unique: list[GroupChatParticipant] = []
    for participant in ordered:
        if participant.agent_id in seen:
            continue
        seen.add(participant.agent_id)
        unique.append(participant)
    return unique


def rotate_participants(
    participants: Sequence[GroupChatParticipant],
    start_index: int,
) -> list[GroupChatParticipant]:
    if not participants:
        return []
    size = len(participants)
    index = start_index % size
    return [*participants[index:], *participants[:index]]


def build_group_chat_plan(
    *,
    mode: object | None,
    participants: Sequence[GroupChatParticipant],
    current_turn_index: int = 0,
    anchor_agent_id: int | None = None,
    direct_recipient_ids: Sequence[int] | None = None,
    pause_seconds: float | None = None,
    coordinator_agent_id: int | None = None,
) -> GroupChatPlan:
    chat_mode = normalize_group_chat_mode(mode)
    ordered_participants = unique_participants(
        participants,
        preferred_agent_id=anchor_agent_id,
    )
    if not ordered_participants:
        return GroupChatPlan(
            mode=chat_mode,
            turns=[],
            awaits_user=True,
            continue_automatically=False,
            pause_seconds=pause_seconds,
            next_turn_index=0,
            coordinator_agent_id=coordinator_agent_id,
        )

    if chat_mode == "continuous":
        rotated = rotate_participants(ordered_participants, current_turn_index)
        return GroupChatPlan(
            mode=chat_mode,
            turns=[
                GroupChatTurn(
                    speaker_agent_id=participant.agent_id,
                    speaker_name=participant.name,
                    turn_prompt=build_turn_prompt(
                        mode=chat_mode,
                        speaker_name=participant.name,
                        coordinator_agent_id=coordinator_agent_id,
                    ),
                )
                for participant in rotated
            ],
            awaits_user=True,
            continue_automatically=False,
            pause_seconds=0.0,
            next_turn_index=(current_turn_index + len(rotated)) % len(ordered_participants),
            coordinator_agent_id=coordinator_agent_id,
        )

    if chat_mode == "auto_paced":
        index = current_turn_index % len(ordered_participants)
        speaker = ordered_participants[index]
        return GroupChatPlan(
            mode=chat_mode,
            turns=[
                GroupChatTurn(
                    speaker_agent_id=speaker.agent_id,
                    speaker_name=speaker.name,
                    turn_prompt=build_turn_prompt(
                        mode=chat_mode,
                        speaker_name=speaker.name,
                        coordinator_agent_id=coordinator_agent_id,
                    ),
                )
            ],
            awaits_user=False,
            continue_automatically=True,
            pause_seconds=pause_seconds,
            next_turn_index=(index + 1) % len(ordered_participants),
            coordinator_agent_id=coordinator_agent_id,
        )

    if chat_mode == "direct":
        if direct_recipient_ids:
            recipients = [
                participant
                for participant in ordered_participants
                if participant.agent_id in {int(agent_id) for agent_id in direct_recipient_ids}
                and participant.agent_id != anchor_agent_id
            ]
        elif anchor_agent_id is None:
            recipients = list(ordered_participants)
        else:
            recipients = [
                participant
                for participant in ordered_participants
                if participant.agent_id != anchor_agent_id
            ]

        return GroupChatPlan(
            mode=chat_mode,
            turns=[
                GroupChatTurn(
                    speaker_agent_id=participant.agent_id,
                    speaker_name=participant.name,
                    turn_prompt=build_turn_prompt(
                        mode=chat_mode,
                        speaker_name=participant.name,
                        coordinator_agent_id=coordinator_agent_id,
                    ),
                )
                for participant in recipients
            ],
            awaits_user=True,
            continue_automatically=False,
            pause_seconds=pause_seconds,
            next_turn_index=current_turn_index % len(ordered_participants),
            coordinator_agent_id=coordinator_agent_id,
        )

    rotated = rotate_participants(ordered_participants, current_turn_index)
    return GroupChatPlan(
        mode=chat_mode,
        turns=[
            GroupChatTurn(
                speaker_agent_id=participant.agent_id,
                speaker_name=participant.name,
                turn_prompt=build_turn_prompt(
                    mode=chat_mode,
                    speaker_name=participant.name,
                    coordinator_agent_id=coordinator_agent_id,
                ),
            )
            for participant in rotated
        ],
        awaits_user=True,
        continue_automatically=False,
        pause_seconds=pause_seconds,
        next_turn_index=(current_turn_index + len(rotated)) % len(ordered_participants),
        coordinator_agent_id=coordinator_agent_id,
    )


def build_turn_prompt(
    *,
    mode: GroupChatMode,
    speaker_name: str,
    coordinator_agent_id: int | None = None,
) -> str:
    if mode == "auto_paced":
        return (
            "Reply naturally to continue the group chat. "
            "The discussion is running in an automatic turn loop, so keep your reply "
            "coherent and forward-moving."
        )

    if mode == "continuous":
        return (
            "Reply naturally to continue the group chat. "
            "The discussion is running continuously with no pause between turns, so keep your reply "
            "coherent and forward-moving."
        )

    if mode == "direct":
        return (
            "Reply directly to the people being addressed. "
            "If the message does not require a long answer, keep it concise and specific."
        )

    coordinator_note = ""
    if coordinator_agent_id is not None:
        coordinator_note = (
            f" A coordinator agent with ID {coordinator_agent_id} may later organize the next round."
        )
    return (
        "Speak once in turn, then yield to the next participant. "
        "After every participant has spoken, the conversation should pause and wait for the user."
        f"{coordinator_note}"
    )
