"""Compatibility entrypoint for framework-neutral module-view normalization.

New interfaces and modules must import from ``apmatia.core.view_contract``. This module remains
temporarily so existing Streamlit imports keep working during the renderer migration.
"""

from apmatia.core.view_contract.normalization import adapt_module_view

__all__ = ["adapt_module_view"]
