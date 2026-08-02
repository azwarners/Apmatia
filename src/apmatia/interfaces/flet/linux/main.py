"""Packaged Flet entry point for the Apmatia Linux Client."""

import flet as ft

from apmatia.interfaces.flet.linux.app import main


if __name__ == "__main__":
    ft.run(main)
