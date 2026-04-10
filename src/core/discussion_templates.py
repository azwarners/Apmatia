from __future__ import annotations

import re


ROLE_PREFIX_RE = re.compile(r"(?m)^(User|Assistant):\s?")

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
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.extend(parse_conversation_messages(existing_content))
    messages.append({"role": "user", "content": current_prompt})
    return messages


def parse_conversation_messages(content: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
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
        text = content[match.end() : next_start].strip()
        if not text:
            continue
        messages.append({"role": role, "content": text})

    return messages
