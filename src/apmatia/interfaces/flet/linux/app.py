"""Flet entry point for the Apmatia Linux Client."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import flet as ft

from ..common.api_client import ApmatiaApiClient
from ..common.errors import AdapterError
from .configuration import ClientConfiguration
from .startup import connected_view, disconnected_view
from .shell import ApmatiaShell


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("flet_debug.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("apmatia.flet.linux")
logger.setLevel(logging.INFO)
logging.getLogger("flet").setLevel(logging.WARNING)
logging.getLogger("flet_desktop").setLevel(logging.WARNING)


def configure_window(page: ft.Page, configuration: ClientConfiguration) -> None:
    """Apply the Linux client window configuration."""
    page.title = "Apmatia"
    page.window.width = configuration.window_width
    page.window.height = configuration.window_height
    page.window.min_width = configuration.minimum_window_width
    page.window.min_height = configuration.minimum_window_height
    icon_path = Path(__file__).resolve().parents[5] / "assets" / "icon.png"
    if icon_path.is_file():
        page.window.icon = str(icon_path)
    page.theme_mode = ft.ThemeMode.SYSTEM


def main(
    page: ft.Page,
    *,
    configuration: ClientConfiguration | None = None,
    api_client: ApmatiaApiClient | None = None,
) -> None:
    """Launch the native Linux client and check Core connectivity."""
    configuration = configuration or ClientConfiguration.from_environment()
    api_client = api_client or ApmatiaApiClient(configuration.core_url)

    configure_window(page, configuration)
    logger.info("Starting Apmatia Linux Client with Core endpoint %s", configuration.core_url)

    def show_connecting() -> None:
        page.controls.clear()
        page.add(
            ft.Container(
                content=ft.Column(
                    [ft.ProgressRing(), ft.Text("Connecting to Apmatia Core...")],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        )
        page.update()

    def check_core(event: ft.ControlEvent | None = None) -> None:
        del event
        show_connecting()
        try:
            version = api_client.get_version()
        except AdapterError as error:
            logger.warning("Apmatia Core connection failed: %s", error)
            page.controls.clear()
            page.add(disconnected_view(configuration, str(error), check_core))
        except Exception as error:  # noqa: BLE001
            logger.exception("Unexpected startup failure")
            page.controls.clear()
            page.add(disconnected_view(configuration, f"Unexpected error: {error}", check_core))
        else:
            logger.info("Connected to Apmatia Core version %s", version)
            page.controls.clear()
            shell = ApmatiaShell(page, api_client, core_version=version)
            page.on_route_change = shell.on_route_change
            shell.start()
        page.update()

    check_core()


if __name__ == "__main__":
    ft.run(main)
