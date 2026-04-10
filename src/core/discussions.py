from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.core.discussion_templates import (
    DISCUSSION_CHAT_TEMPLATE,
    build_chat_messages,
)
from src.core.prompt_LLM import prompt_llm
from src.core.app_config import get_config_value, load_app_config, save_app_config


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DISCUSSIONS_DIR = APP_DIR / "discussions"


def _new_discussion_id() -> str:
    return f"ID{uuid.uuid4().hex[:8]}"


@dataclass
class DiscussionSnapshot:
    discussion_id: str
    is_streaming: bool
    last_error: str | None
    system_prompt: str
    content: str


class DiscussionState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._is_streaming = False
        self._last_error: str | None = None
        self._system_prompt = ""
        self._discussion_id = self._load_or_init_discussion_id()

    def _load_or_init_discussion_id(self) -> str:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        DISCUSSIONS_DIR.mkdir(parents=True, exist_ok=True)

        discussion_id = get_config_value("discussion", "current_discussion_id", default=None)
        system_prompt = get_config_value("discussion", "system_prompt", default="")
        if isinstance(system_prompt, str):
            self._system_prompt = system_prompt
        if discussion_id:
            return str(discussion_id)

        new_discussion_id = _new_discussion_id()
        self._save_state(new_discussion_id, self._system_prompt)
        return new_discussion_id

    def _save_state(self, discussion_id: str, system_prompt: str) -> None:
        config = load_app_config()
        discussion = dict(config.get("discussion", {}))
        discussion["current_discussion_id"] = discussion_id
        discussion["system_prompt"] = system_prompt
        config["discussion"] = discussion
        save_app_config(config)

    def _discussion_path(self, discussion_id: str) -> Path:
        return DISCUSSIONS_DIR / f"{discussion_id}.txt"

    def _append_text(self, discussion_id: str, text: str) -> None:
        path = self._discussion_path(discussion_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
            file.flush()

    def _run_prompt(self, discussion_id: str, prompt: str) -> None:
        try:
            discussion_path = self._discussion_path(discussion_id)
            existing_content = (
                discussion_path.read_text(encoding="utf-8")
                if discussion_path.exists()
                else ""
            )
            with self._lock:
                system_prompt = self._system_prompt

            chat_messages = build_chat_messages(
                existing_content=existing_content,
                system_prompt=system_prompt,
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
        except Exception as error:
            with self._lock:
                self._last_error = str(error)
        finally:
            with self._lock:
                self._is_streaming = False
                self._thread = None

    def start_prompt(self, prompt: str) -> str:
        with self._lock:
            if self._is_streaming:
                raise RuntimeError("A discussion response is already streaming.")

            self._is_streaming = True
            self._last_error = None
            discussion_id = self._discussion_id
            self._thread = threading.Thread(
                target=self._run_prompt,
                args=(discussion_id, prompt),
                daemon=True,
            )
            self._thread.start()
            return discussion_id

    def reset_discussion(self) -> str:
        with self._lock:
            if self._is_streaming:
                raise RuntimeError("Cannot reset while a response is still streaming.")

            self._discussion_id = _new_discussion_id()
            self._last_error = None
            self._save_state(self._discussion_id, self._system_prompt)
            return self._discussion_id

    def set_system_prompt(self, system_prompt: str) -> None:
        with self._lock:
            self._system_prompt = system_prompt
            self._save_state(self._discussion_id, self._system_prompt)

    def snapshot(self) -> DiscussionSnapshot:
        with self._lock:
            discussion_id = self._discussion_id
            is_streaming = self._is_streaming
            last_error = self._last_error
            system_prompt = self._system_prompt

        path = self._discussion_path(discussion_id)
        content = path.read_text(encoding="utf-8") if path.exists() else ""

        return DiscussionSnapshot(
            discussion_id=discussion_id,
            is_streaming=is_streaming,
            last_error=last_error,
            system_prompt=system_prompt,
            content=content,
        )

discussion_state = DiscussionState()
