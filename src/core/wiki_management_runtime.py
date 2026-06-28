from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.lib.wiki_management.module import WikiManager

if TYPE_CHECKING:
    from src.lib.wiki_management.sqlite_repositories import SQLiteWikiManagementBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
WIKI_DB_PATH = DATA_DIR / "wikis.db"


_bundle: "SQLiteWikiManagementBundle | None" = None
_wiki_manager: "WikiManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _wiki_manager

    if _bundle is None:
        from src.lib.wiki_management.sqlite_repositories import SQLiteWikiManagementBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteWikiManagementBundle(WIKI_DB_PATH)
        _wiki_manager = WikiManager(_bundle.wikis, _bundle.nodes)


def get_wiki_manager() -> WikiManager:
    _ensure_runtime()
    assert _wiki_manager is not None
    return _wiki_manager

