from __future__ import annotations

from typing import Protocol

from .models import Discussion, DiscussionParticipant, DiscussionTurn, Topic, TopicSummary


class TopicRepository(Protocol):
    def create(self, topic: Topic) -> str | int:
        raise NotImplementedError

    def get(self, topic_id: str | int) -> Topic | None:
        raise NotImplementedError

    def list_all(self) -> list[Topic]:
        raise NotImplementedError

    def update(self, topic: Topic) -> None:
        raise NotImplementedError

    def delete(self, topic_id: str | int) -> bool:
        raise NotImplementedError


class DiscussionRepository(Protocol):
    def create(self, discussion: Discussion) -> str | int:
        raise NotImplementedError

    def get(self, discussion_id: str | int) -> Discussion | None:
        raise NotImplementedError

    def list_all(self) -> list[Discussion]:
        raise NotImplementedError

    def list_by_topic(self, topic_id: str | int) -> list[Discussion]:
        raise NotImplementedError

    def update(self, discussion: Discussion) -> None:
        raise NotImplementedError

    def delete(self, discussion_id: str | int) -> bool:
        raise NotImplementedError


class DiscussionParticipantRepository(Protocol):
    def create(self, participant: DiscussionParticipant) -> str | int:
        raise NotImplementedError

    def get(self, participant_id: str | int) -> DiscussionParticipant | None:
        raise NotImplementedError

    def list_all(self) -> list[DiscussionParticipant]:
        raise NotImplementedError

    def list_by_discussion(self, discussion_id: str | int) -> list[DiscussionParticipant]:
        raise NotImplementedError

    def update(self, participant: DiscussionParticipant) -> None:
        raise NotImplementedError

    def delete(self, participant_id: str | int) -> bool:
        raise NotImplementedError


class TopicSummaryRepository(Protocol):
    def create(self, summary: TopicSummary) -> str | int:
        raise NotImplementedError

    def get(self, summary_id: str | int) -> TopicSummary | None:
        raise NotImplementedError

    def list_all(self) -> list[TopicSummary]:
        raise NotImplementedError

    def list_by_topic(self, topic_id: str | int) -> list[TopicSummary]:
        raise NotImplementedError

    def update(self, summary: TopicSummary) -> None:
        raise NotImplementedError

    def delete(self, summary_id: str | int) -> bool:
        raise NotImplementedError


class DiscussionTurnRepository(Protocol):
    def create(self, turn: DiscussionTurn) -> str | int:
        raise NotImplementedError

    def get(self, turn_id: str | int) -> DiscussionTurn | None:
        raise NotImplementedError

    def list_all(self) -> list[DiscussionTurn]:
        raise NotImplementedError

    def list_by_discussion(self, discussion_id: str | int) -> list[DiscussionTurn]:
        raise NotImplementedError

    def update(self, turn: DiscussionTurn) -> None:
        raise NotImplementedError

    def delete(self, turn_id: str | int) -> bool:
        raise NotImplementedError

