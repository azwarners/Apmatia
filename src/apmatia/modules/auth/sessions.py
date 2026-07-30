from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class AuthSession:
    token: str
    user_id: int
    username: str
    expires_at: datetime


class SessionManager:
    def __init__(self, storage_path: Path | str | None = None) -> None:
        self._lock = threading.Lock()
        self._storage_path = Path(storage_path).expanduser() if storage_path is not None else None
        self._sessions: dict[str, AuthSession] = {}
        self._load_sessions()

    def create_session(self, user_id: int, username: str) -> AuthSession:
        token = secrets.token_urlsafe(32)
        session = AuthSession(
            token=token,
            user_id=user_id,
            username=username,
            expires_at=_utc_now() + timedelta(seconds=DEFAULT_SESSION_TTL_SECONDS),
        )
        with self._lock:
            self._sessions[token] = session
            self._save_sessions_locked()
        return session

    def get_session(self, token: str | None) -> AuthSession | None:
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expires_at <= _utc_now():
                self._sessions.pop(token, None)
                self._save_sessions_locked()
                return None
            return session

    def delete_session(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            removed = self._sessions.pop(token, None) is not None
            if removed:
                self._save_sessions_locked()
            return removed

    def _load_sessions(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        sessions: dict[str, AuthSession] = {}
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict):
                continue
            token = item.get("token")
            user_id = item.get("user_id")
            username = item.get("username")
            expires_at = item.get("expires_at")
            if not all(isinstance(value, (str, int)) for value in (token, user_id, username, expires_at)):
                continue
            try:
                session = AuthSession(
                    token=str(token),
                    user_id=int(user_id),
                    username=str(username),
                    expires_at=datetime.fromisoformat(str(expires_at)),
                )
            except ValueError:
                continue
            if session.expires_at > _utc_now():
                sessions[session.token] = session
        self._sessions = sessions

    def _save_sessions_locked(self) -> None:
        if self._storage_path is None:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._storage_path.with_suffix(f"{self._storage_path.suffix}.tmp")
        payload = [
            {
                "token": session.token,
                "user_id": session.user_id,
                "username": session.username,
                "expires_at": session.expires_at.isoformat(),
            }
            for session in self._sessions.values()
        ]
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self._storage_path)
