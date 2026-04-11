from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from persistence import SQLiteStore
except ModuleNotFoundError:
    from src.libraries.persistence.persistence import SQLiteStore

from src.core.discussion_templates import DISCUSSION_CHAT_TEMPLATE, build_chat_messages
from src.core.prompt_LLM import prompt_llm


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
DISCUSSIONS_DIR = DATA_DIR / "discussions"
DISCUSSIONS_DB = DATA_DIR / "discussions.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_discussion_id() -> str:
    return f"ID{uuid.uuid4().hex[:8]}"


@dataclass(slots=True)
class DiscussionSnapshot:
    discussion_id: str
    is_streaming: bool
    last_error: str | None
    system_prompt: str
    content: str


class DiscussionState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DISCUSSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._store = SQLiteStore(DISCUSSIONS_DB)
        self._threads: dict[str, threading.Thread] = {}
        self._streaming: set[str] = set()

    def _discussion_path(self, discussion_id: str) -> Path:
        return DISCUSSIONS_DIR / f"{discussion_id}.txt"

    def _append_text(self, discussion_id: str, text: str) -> None:
        path = self._discussion_path(discussion_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
            file.flush()

    def _get_discussion(self, discussion_id: str) -> dict | None:
        return self._store.get("discussions", discussion_id=discussion_id)

    def _update_discussion(self, discussion_id: str, data: dict) -> None:
        row = self._store.get("discussions", discussion_id=discussion_id)
        if not row:
            raise ValueError(f"Discussion not found: {discussion_id}")
        data["updated_at"] = utc_now_iso()
        self._store.update("discussions", where={"id": row["id"]}, data=data)

    def _create_discussion(
        self,
        owner_user_id: int,
        title: str = "Untitled Discussion",
        group_id: int | None = None,
        folder_id: int | None = None,
    ) -> dict:
        discussion_id = _new_discussion_id()
        visibility = "group" if group_id is not None else "private"
        created_at = utc_now_iso()
        row = {
            "discussion_id": discussion_id,
            "title": title,
            "owner_user_id": owner_user_id,
            "group_id": group_id,
            "visibility": visibility,
            "folder_id": folder_id,
            "system_prompt": "",
            "last_error": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
        self._store.insert("discussions", row)
        return row

    def _set_current_discussion(self, user_id: int, discussion_id: str) -> None:
        row = self._store.get("discussion_user_state", user_id=user_id)
        if row:
            self._store.update(
                "discussion_user_state",
                where={"id": row["id"]},
                data={"user_id": user_id, "current_discussion_id": discussion_id},
            )
        else:
            self._store.insert(
                "discussion_user_state",
                {"user_id": user_id, "current_discussion_id": discussion_id},
            )

    def _get_current_discussion_id(self, user_id: int) -> str | None:
        row = self._store.get("discussion_user_state", user_id=user_id)
        if not row:
            return None
        current_discussion_id = row.get("current_discussion_id")
        return None if current_discussion_id is None else str(current_discussion_id)

    def _is_visible(self, discussion: dict, user_id: int, member_group_ids: set[int]) -> bool:
        owner_user_id = int(discussion.get("owner_user_id", 0))
        if owner_user_id == user_id:
            return True

        group_id = discussion.get("group_id")
        if group_id is None:
            return False
        return int(group_id) in member_group_ids

    def _get_or_create_current_discussion(self, user_id: int, member_group_ids: set[int]) -> dict:
        current_discussion_id = self._get_current_discussion_id(user_id)
        if current_discussion_id:
            current = self._get_discussion(current_discussion_id)
            if current and self._is_visible(current, user_id, member_group_ids):
                return current

        created = self._create_discussion(owner_user_id=user_id, title="New Discussion")
        self._set_current_discussion(user_id, created["discussion_id"])
        return created

    def _run_prompt(self, discussion_id: str, prompt: str) -> None:
        try:
            discussion = self._get_discussion(discussion_id)
            if not discussion:
                raise RuntimeError(f"Discussion not found: {discussion_id}")

            discussion_path = self._discussion_path(discussion_id)
            existing_content = discussion_path.read_text(encoding="utf-8") if discussion_path.exists() else ""
            chat_messages = build_chat_messages(
                existing_content=existing_content,
                system_prompt=str(discussion.get("system_prompt", "")),
                current_prompt=prompt,
            )
            self._append_text(discussion_id, f"\nUser: {prompt}\nAssistant: ")
            prompt_llm(
                prompt=prompt,
                output_dir=str(DISCUSSIONS_DIR),
                prompt_id=discussion_id,
                append_existing=True,
                context=None,
                request_metadata={
                    "chat_template": DISCUSSION_CHAT_TEMPLATE,
                    "chat_messages": chat_messages,
                    "add_generation_prompt": True,
                },
            )
            self._append_text(discussion_id, "\n")
            self._update_discussion(discussion_id, {"last_error": None})
        except Exception as error:
            self._update_discussion(discussion_id, {"last_error": str(error)})
        finally:
            with self._lock:
                self._streaming.discard(discussion_id)
                self._threads.pop(discussion_id, None)

    def create_folder(self, owner_user_id: int, name: str, parent_id: int | None = None) -> dict:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Folder name cannot be empty.")

        if parent_id is not None:
            parent = self._store.get("discussion_folders", id=parent_id)
            if not parent or int(parent.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Parent folder not found.")

        created_at = utc_now_iso()
        folder = {
            "name": clean_name,
            "parent_id": parent_id,
            "owner_user_id": owner_user_id,
            "created_at": created_at,
            "updated_at": created_at,
        }
        folder_id = self._store.insert("discussion_folders", folder)
        return {"id": folder_id, **folder}

    def update_folder(
        self,
        owner_user_id: int,
        folder_id: int,
        name: str | None = None,
        parent_id: int | None = None,
    ) -> dict:
        folder = self._store.get("discussion_folders", id=folder_id)
        if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
            raise ValueError("Folder not found.")

        updates: dict = {}
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Folder name cannot be empty.")
            updates["name"] = clean_name

        if parent_id is not None:
            if parent_id == folder_id:
                raise ValueError("Folder cannot be its own parent.")
            parent = self._store.get("discussion_folders", id=parent_id)
            if not parent or int(parent.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Parent folder not found.")
            updates["parent_id"] = parent_id

        if updates:
            updates["updated_at"] = utc_now_iso()
            self._store.update("discussion_folders", where={"id": folder_id}, data=updates)

        merged = {**folder, **updates}
        return merged

    def create_discussion(
        self,
        owner_user_id: int,
        title: str,
        group_id: int | None = None,
        folder_id: int | None = None,
    ) -> dict:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Discussion title cannot be empty.")

        if folder_id is not None:
            folder = self._store.get("discussion_folders", id=folder_id)
            if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Folder not found.")

        created = self._create_discussion(
            owner_user_id=owner_user_id,
            title=clean_title,
            group_id=group_id,
            folder_id=folder_id,
        )
        return created

    def update_discussion(
        self,
        owner_user_id: int,
        discussion_id: str,
        title: str | None = None,
        group_id: int | None = None,
        folder_id: int | None = None,
    ) -> dict:
        discussion = self._get_discussion(discussion_id)
        if not discussion or int(discussion.get("owner_user_id", -1)) != owner_user_id:
            raise ValueError("Discussion not found.")

        updates: dict = {}
        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Discussion title cannot be empty.")
            updates["title"] = clean_title

        updates["group_id"] = group_id
        updates["visibility"] = "group" if group_id is not None else "private"

        if folder_id is not None:
            folder = self._store.get("discussion_folders", id=folder_id)
            if not folder or int(folder.get("owner_user_id", -1)) != owner_user_id:
                raise ValueError("Folder not found.")
            updates["folder_id"] = folder_id

        self._update_discussion(discussion_id, updates)
        return {**discussion, **updates}

    def open_discussion(self, user_id: int, discussion_id: str, member_group_ids: set[int]) -> None:
        discussion = self._get_discussion(discussion_id)
        if not discussion or not self._is_visible(discussion, user_id, member_group_ids):
            raise ValueError("Discussion not found.")
        self._set_current_discussion(user_id, discussion_id)

    def list_tree(self, user_id: int, member_group_ids: set[int]) -> dict:
        folders = self._store.find("discussion_folders", owner_user_id=user_id)
        all_discussions = self._store.find("discussions")
        visible = [
            discussion
            for discussion in all_discussions
            if self._is_visible(discussion, user_id, member_group_ids)
        ]
        current_discussion_id = self._get_current_discussion_id(user_id)
        return {
            "current_discussion_id": current_discussion_id,
            "folders": folders,
            "discussions": visible,
        }

    def start_prompt(self, user_id: int, prompt: str, member_group_ids: set[int]) -> str:
        with self._lock:
            discussion = self._get_or_create_current_discussion(user_id, member_group_ids)
            discussion_id = str(discussion["discussion_id"])
            if discussion_id in self._streaming:
                raise RuntimeError("A discussion response is already streaming.")

            self._streaming.add(discussion_id)
            self._update_discussion(discussion_id, {"last_error": None})
            thread = threading.Thread(
                target=self._run_prompt,
                args=(discussion_id, prompt),
                daemon=True,
            )
            self._threads[discussion_id] = thread
            thread.start()
            return discussion_id

    def reset_discussion(self, user_id: int) -> str:
        with self._lock:
            current = self._get_or_create_current_discussion(user_id, set())
            current_id = str(current["discussion_id"])
            if current_id in self._streaming:
                raise RuntimeError("Cannot reset while a response is still streaming.")

            created = self._create_discussion(owner_user_id=user_id, title="New Discussion")
            self._set_current_discussion(user_id, created["discussion_id"])
            return str(created["discussion_id"])

    def set_system_prompt(self, user_id: int, system_prompt: str, member_group_ids: set[int]) -> None:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        self._update_discussion(
            str(current["discussion_id"]),
            {"system_prompt": system_prompt},
        )

    def snapshot(self, user_id: int, member_group_ids: set[int]) -> DiscussionSnapshot:
        current = self._get_or_create_current_discussion(user_id, member_group_ids)
        discussion_id = str(current["discussion_id"])
        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""

        with self._lock:
            is_streaming = discussion_id in self._streaming

        return DiscussionSnapshot(
            discussion_id=discussion_id,
            is_streaming=is_streaming,
            last_error=None if current.get("last_error") is None else str(current.get("last_error")),
            system_prompt=str(current.get("system_prompt", "")),
            content=content,
        )


discussion_state = DiscussionState()
