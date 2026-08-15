"""Tests for the Flet API client's session persistence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from apmatia.interfaces.flet.common.api_client import ApmatiaApiClient


def test_login_persists_only_the_session_cookie(tmp_path: Path, monkeypatch) -> None:
    session_path = tmp_path / "flet-session.json"
    monkeypatch.setenv("APMATIA_FLET_SESSION_FILE", str(session_path))

    client = ApmatiaApiClient("http://core/api")
    response = Mock()
    response.json.return_value = {"status": "authenticated"}

    def request(*_args, **_kwargs):
        client.session.cookies.set("apmatia_session", "session-token")
        return response

    client.session.request = request

    client.login("nick", "secret")

    assert json.loads(session_path.read_text(encoding="utf-8")) == {"token": "session-token"}
    assert session_path.stat().st_mode & 0o777 == 0o600
    assert "secret" not in session_path.read_text(encoding="utf-8")


def test_new_client_restores_persisted_cookie(tmp_path: Path, monkeypatch) -> None:
    session_path = tmp_path / "flet-session.json"
    session_path.write_text(json.dumps({"token": "session-token"}), encoding="utf-8")
    monkeypatch.setenv("APMATIA_FLET_SESSION_FILE", str(session_path))

    client = ApmatiaApiClient("http://core/api")

    assert client.session.cookies.get("apmatia_session") == "session-token"


def test_logout_removes_persisted_cookie(tmp_path: Path, monkeypatch) -> None:
    session_path = tmp_path / "flet-session.json"
    session_path.write_text(json.dumps({"token": "session-token"}), encoding="utf-8")
    monkeypatch.setenv("APMATIA_FLET_SESSION_FILE", str(session_path))

    client = ApmatiaApiClient("http://core/api")
    response = Mock()
    response.json.return_value = {"status": "logged_out"}
    client.session.request = Mock(return_value=response)

    client.logout()

    assert not session_path.exists()
