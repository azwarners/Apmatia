"""Tests for the Phase 1 Linux client launcher."""

from __future__ import annotations

from unittest.mock import Mock

import flet as ft

from apmatia.interfaces.flet.common.api_client import ApmatiaApiClient
from apmatia.interfaces.flet.linux.app import main
from apmatia.interfaces.flet.linux.configuration import ClientConfiguration, normalize_core_url


def test_normalize_core_url_accepts_server_and_api_roots() -> None:
    assert normalize_core_url("http://localhost:8000") == "http://localhost:8000/api"
    assert normalize_core_url("http://localhost:8000/api/") == "http://localhost:8000/api"


def test_client_configuration_reads_release_runtime_environment(monkeypatch) -> None:
    monkeypatch.setenv("APMATIA_API_URL", "http://core:8000")
    monkeypatch.setenv("APMATIA_FLET_WINDOW_WIDTH", "1280")
    monkeypatch.setenv("APMATIA_FLET_WINDOW_HEIGHT", "800")

    configuration = ClientConfiguration.from_environment()

    assert configuration.core_url == "http://core:8000/api"
    assert configuration.window_width == 1280
    assert configuration.window_height == 800


def test_api_client_uses_api_root_by_default() -> None:
    client = ApmatiaApiClient()
    assert client.base_url == "http://127.0.0.1:8000/api"


def test_api_client_reads_core_version() -> None:
    client = ApmatiaApiClient("http://core/api")
    client._request = Mock(return_value={"version": "1.2.3"})  # type: ignore[method-assign]
    assert client.get_version() == "1.2.3"
    client._request.assert_called_once_with("GET", "/version")


def test_launcher_shows_connected_startup_view() -> None:
    page = FakePage()
    api_client = Mock()
    api_client.get_version.return_value = "1.2.3"
    main(page, configuration=ClientConfiguration(core_url="http://core/api"), api_client=api_client)
    assert page.title == "Apmatia"
    assert len(page.controls) == 1
    assert "Connected to Apmatia Core" in _control_text(page.controls[0])


def test_launcher_uses_the_normal_apmatia_icon() -> None:
    page = FakePage()
    main(page, configuration=ClientConfiguration(core_url="http://core/api"), api_client=Mock(get_version=Mock(return_value="1.2.3")))
    assert page.window.icon.endswith("/assets/icon.png")


def test_launcher_shows_actionable_error_when_core_is_unavailable() -> None:
    page = FakePage()
    api_client = Mock()
    api_client.get_version.side_effect = ConnectionError("connection refused")
    main(page, configuration=ClientConfiguration(core_url="http://core/api"), api_client=api_client)
    assert len(page.controls) == 1
    text = _control_text(page.controls[0])
    assert "Unable to connect to Apmatia Core" in text
    assert "http://core/api" in text
    assert "retry" in text.lower()


def _control_text(control: ft.Control) -> str:
    values: list[str] = []
    if isinstance(control, ft.Text) and control.value:
        values.append(control.value)
    for child in getattr(control, "controls", []) or []:
        values.append(_control_text(child))
    content = getattr(control, "content", None)
    if content is not None:
        values.append(_control_text(content))
    return " ".join(values)


class FakePage:
    """Small page double that models the methods used by the launcher."""

    def __init__(self) -> None:
        self.controls: list[ft.Control] = []
        self.window = Mock()
        self.theme_mode = None
        self.title = None

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        pass
