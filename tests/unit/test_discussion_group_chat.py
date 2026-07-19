from apmatia.lib.discussions.group_chat import (
    GroupChatParticipant,
    build_group_chat_plan,
    build_turn_prompt,
    normalize_group_chat_mode,
)


def test_normalize_group_chat_mode_defaults_to_round_robin():
    assert normalize_group_chat_mode(None) == "round_robin"
    assert normalize_group_chat_mode("ROUND_ROBIN") == "round_robin"
    assert normalize_group_chat_mode("continuous") == "continuous"
    assert normalize_group_chat_mode("unknown") == "round_robin"


def test_round_robin_plan_keeps_participants_in_turn_order():
    participants = [
        GroupChatParticipant(agent_id=7, name="Alpha"),
        GroupChatParticipant(agent_id=8, name="Beta"),
        GroupChatParticipant(agent_id=9, name="Gamma"),
    ]

    plan = build_group_chat_plan(
        mode="round_robin",
        participants=participants,
        current_turn_index=0,
        anchor_agent_id=8,
    )

    assert [turn.speaker_agent_id for turn in plan.turns] == [8, 7, 9]
    assert plan.awaits_user is True
    assert plan.continue_automatically is False
    assert plan.next_turn_index == 0


def test_auto_paced_plan_advances_one_turn_at_a_time():
    participants = [
        GroupChatParticipant(agent_id=7, name="Alpha"),
        GroupChatParticipant(agent_id=8, name="Beta"),
    ]

    plan = build_group_chat_plan(
        mode="auto_paced",
        participants=participants,
        current_turn_index=1,
        pause_seconds=2.5,
    )

    assert [turn.speaker_agent_id for turn in plan.turns] == [8]
    assert plan.next_turn_index == 0
    assert plan.pause_seconds == 2.5
    assert plan.continue_automatically is True


def test_continuous_plan_continues_without_pause():
    participants = [
        GroupChatParticipant(agent_id=7, name="Alpha"),
        GroupChatParticipant(agent_id=8, name="Beta"),
    ]

    plan = build_group_chat_plan(
        mode="continuous",
        participants=participants,
        current_turn_index=1,
    )

    assert [turn.speaker_agent_id for turn in plan.turns] == [8, 7]
    assert plan.pause_seconds == 0.0
    assert plan.continue_automatically is False
    assert plan.next_turn_index == 1


def test_round_robin_plan_advances_to_the_next_starting_speaker():
    participants = [
        GroupChatParticipant(agent_id=7, name="Alpha"),
        GroupChatParticipant(agent_id=8, name="Beta"),
        GroupChatParticipant(agent_id=9, name="Gamma"),
    ]

    plan = build_group_chat_plan(
        mode="round_robin",
        participants=participants,
        current_turn_index=2,
    )

    assert [turn.speaker_agent_id for turn in plan.turns] == [9, 7, 8]
    assert plan.next_turn_index == 2


def test_direct_plan_avoids_the_anchor_agent_when_no_targets_are_supplied():
    participants = [
        GroupChatParticipant(agent_id=7, name="Alpha"),
        GroupChatParticipant(agent_id=8, name="Beta"),
        GroupChatParticipant(agent_id=9, name="Gamma"),
    ]

    plan = build_group_chat_plan(
        mode="direct",
        participants=participants,
        anchor_agent_id=7,
    )

    assert [turn.speaker_agent_id for turn in plan.turns] == [8, 9]
    assert plan.awaits_user is True


def test_turn_prompt_does_not_repeat_agent_identity():
    prompt = build_turn_prompt(mode="round_robin", speaker_name="Alpha")

    assert prompt.startswith("Speak once in turn")
    assert "yield to the next participant" in prompt
    assert "round robin" not in prompt.lower()
    assert "You are Alpha" not in prompt


def test_direct_turn_prompt_does_not_repeat_agent_identity():
    prompt = build_turn_prompt(mode="direct", speaker_name="Alpha")

    assert prompt.startswith("Reply directly")
    assert "You are Alpha" not in prompt
