"""Startup views for the Apmatia Linux Client."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from .configuration import ClientConfiguration


def connected_view(configuration: ClientConfiguration, version: str) -> ft.Control:
    """Build the connected startup view."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Apmatia", size=32, weight=ft.FontWeight.BOLD),
                ft.Text("Connected to Apmatia Core", color=ft.Colors.GREEN_700),
                ft.Text(f"Core version: {version}"),
                ft.Text(f"Endpoint: {configuration.core_url}"),
                ft.Text("The Linux client is ready for the next migration phase."),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def disconnected_view(
    configuration: ClientConfiguration,
    message: str,
    on_retry: Callable[[ft.ControlEvent], None],
) -> ft.Control:
    """Build an actionable disconnected startup view."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Apmatia", size=32, weight=ft.FontWeight.BOLD),
                ft.Text("Unable to connect to Apmatia Core", color=ft.Colors.RED_700),
                ft.Text(message, text_align=ft.TextAlign.CENTER),
                ft.Text(f"Endpoint: {configuration.core_url}"),
                ft.Text("Start Apmatia Core or verify APMATIA_API_URL, then retry."),
                ft.Button("Retry connection", on_click=on_retry),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )
