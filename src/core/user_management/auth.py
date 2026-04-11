from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass

from src.core.user_management.models import UserId


@dataclass(slots=True)
class AuthSession:
    token: str
    user_id: UserId
    username: str


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, AuthSession] = {}

    def create_session(self, user_id: UserId, username: str) -> AuthSession:
        token = secrets.token_urlsafe(32)
        session = AuthSession(token=token, user_id=user_id, username=username)
        with self._lock:
            self._sessions[token] = session
        return session

    def get_session(self, token: str | None) -> AuthSession | None:
        if not token:
            return None
        with self._lock:
            return self._sessions.get(token)

    def delete_session(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            return self._sessions.pop(token, None) is not None

