"""Compatibility shim for the bundled persistence module."""

from apmatia.modules.persistence import load_config_file, save_config_file

__all__ = ["load_config_file", "save_config_file"]
