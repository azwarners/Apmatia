"""Compatibility shim: re-export config persistence from the shared library."""

from persistence.core import load_config_file, save_config_file

__all__ = ["load_config_file", "save_config_file"]
