"""Apmatia source package."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_src_root = Path(__file__).resolve().parent.parent
_src_root_str = str(_src_root)
if _src_root_str not in __path__:
    __path__.append(_src_root_str)
