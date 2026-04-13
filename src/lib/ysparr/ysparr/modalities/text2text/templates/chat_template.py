from __future__ import annotations

from typing import Any, Dict, List

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateError

from ysparr.core.exceptions import ExecutionError


# Small, strict renderer so template mistakes fail fast and clearly.
_ENV = Environment(
    loader=BaseLoader(),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


def render_chat_template(
    template_text: str,
    messages: List[Dict[str, Any]],
    add_generation_prompt: bool = True,
    extra_context: Dict[str, Any] | None = None,
) -> str:
    """
    Render a KoboldCpp-style chat template into a single prompt string.

    Args:
        template_text: Jinja template body.
        messages: Chat message objects, commonly with role/content.
        add_generation_prompt: Common chat-template flag.
        extra_context: Optional additional template variables.

    Returns:
        Fully rendered prompt string.
    """

    if not isinstance(template_text, str) or not template_text.strip():
        raise ExecutionError("chat_template must be a non-empty string")

    if not isinstance(messages, list):
        raise ExecutionError("chat_messages must be a list")

    context: Dict[str, Any] = {
        "messages": messages,
        "add_generation_prompt": add_generation_prompt,
    }
    if isinstance(extra_context, dict):
        context.update(extra_context)

    try:
        template = _ENV.from_string(template_text)
        return template.render(**context)
    except TemplateError as error:
        raise ExecutionError(f"Failed to render chat template: {error}") from error
