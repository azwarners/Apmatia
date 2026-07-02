from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any


ROLE_PREFIX_RE = re.compile(r"(?m)^(User|Assistant|Agent)(?:\s*\((?P<speaker>[^)]+)\))?:\s?")
METADATA_COMMENT_RE = re.compile(r"(?s)<!--\s*apmatia-metadata:\s*.*?\s*-->")

DISCUSSION_CHAT_TEMPLATE = """{% for message in messages -%}
{% if message.role == "system" -%}
System Instructions:
{{ message.content }}

{% elif message.role == "user" -%}
User: {{ message.content }}
{% elif message.role == "assistant" -%}
Assistant: {{ message.content }}
{% endif -%}
{% endfor -%}
{% if add_generation_prompt %}Assistant:{% endif %}"""


def build_chat_messages(
    existing_content: str,
    system_prompt: str,
    current_prompt: str,
    *,
    current_attachments: list[dict[str, Any]] | None = None,
    attachment_resolver: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.extend(
        _message_to_chat_messages(
            message,
            attachment_resolver=attachment_resolver,
        )
        for message in parse_conversation_messages(existing_content)
    )
    messages.append(
        {
            "role": "user",
            "content": _message_content(
                current_prompt,
                current_attachments or [],
                attachment_resolver=attachment_resolver,
            ),
        }
    )
    return messages


def parse_conversation_messages(content: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    matches = list(ROLE_PREFIX_RE.finditer(content))
    if not matches:
        return messages

    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(content)
        )
        role_token = match.group(1)
        role = "user" if role_token == "User" else "assistant"
        text = METADATA_COMMENT_RE.sub("", content[match.end() : next_start]).strip()
        if not text:
            continue
        speaker_name = match.group("speaker")
        if speaker_name:
            text = f"{speaker_name}: {text}"
        message: dict[str, Any] = {"role": role, "content": text}
        metadata_match = re.search(r"<!--\s*apmatia-metadata:\s*(?P<payload>.+?)\s*-->", content[match.end() : next_start], re.S)
        if metadata_match:
            try:
                metadata = json.loads(metadata_match.group("payload").strip())
            except Exception:
                metadata = None
            if isinstance(metadata, dict) and metadata:
                message["metadata"] = metadata
        messages.append(message)

    return messages


def _message_to_chat_messages(
    message: dict[str, Any],
    *,
    attachment_resolver: Callable[[dict[str, Any]], dict[str, Any] | None] | None,
) -> dict[str, Any]:
    content = _message_content(
        str(message.get("content", "")),
        _message_attachments(message),
        attachment_resolver=attachment_resolver,
    )
    return {"role": message.get("role", "assistant"), "content": content}


def _message_attachments(message: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        return []
    attachments = metadata.get("attachments")
    if not isinstance(attachments, list):
        return []
    return [attachment for attachment in attachments if isinstance(attachment, dict)]


def _message_content(
    text: str,
    attachments: list[dict[str, Any]],
    *,
    attachment_resolver: Callable[[dict[str, Any]], dict[str, Any] | None] | None,
) -> str | list[dict[str, Any]]:
    clean_text = text.strip()
    parts: list[dict[str, Any]] = []
    if clean_text:
        parts.append({"type": "text", "text": clean_text})

    for attachment in attachments:
        if attachment_resolver is None:
            continue
        resolved = attachment_resolver(attachment)
        if resolved is not None:
            parts.append(resolved)

    if not parts:
        return ""
    if len(parts) == 1 and parts[0].get("type") == "text":
        return parts[0]["text"]
    return parts
