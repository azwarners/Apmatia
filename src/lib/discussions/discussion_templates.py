from __future__ import annotations

import re
from typing import Any, Callable


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
    attachment_resolver: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    for message in parse_conversation_messages(existing_content):
        messages.append(
            {
                "role": message["role"],
                "content": _build_message_content(
                    str(message.get("content", "")),
                    metadata=message.get("metadata"),
                    attachment_resolver=attachment_resolver,
                ),
            }
        )

    messages.append(
        {
            "role": "user",
            "content": _build_message_content(
                current_prompt,
                metadata={"attachments": current_attachments or []},
                attachment_resolver=attachment_resolver,
            ),
        }
    )
    return messages


def _build_message_content(
    text: str,
    *,
    metadata: dict[str, Any] | None,
    attachment_resolver: Callable[[dict[str, Any]], list[dict[str, Any]]] | None,
) -> str | list[dict[str, Any]]:
    clean_text = str(text or "").strip()
    attachments: list[dict[str, Any]] = []

    if attachment_resolver is not None and isinstance(metadata, dict):
        raw_attachments = metadata.get("attachments")
        if isinstance(raw_attachments, list):
            for attachment in raw_attachments:
                if not isinstance(attachment, dict):
                    continue
                attachments.extend(attachment_resolver(attachment))

    if not attachments:
        return clean_text

    content_parts: list[dict[str, Any]] = []
    if clean_text:
        content_parts.append({"type": "text", "text": clean_text})
    content_parts.extend(attachments)
    return content_parts


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
        messages.append({"role": role, "content": text})

    return messages
