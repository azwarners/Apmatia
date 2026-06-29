from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True, slots=True)
class ModuleTemplateContext:
    module_slug: str
    display_name: str
    description: str
    author: str
    module_id: str
    class_name: str


def build_module_template_context(
    module_slug: str,
    display_name: str,
    description: str = "",
    author: str = "",
) -> ModuleTemplateContext:
    module_id = module_slug
    class_name = "".join(part.capitalize() for part in module_slug.split("_")) or "Module"
    return ModuleTemplateContext(
        module_slug=module_slug,
        display_name=display_name,
        description=description,
        author=author,
        module_id=module_id,
        class_name=class_name,
    )


def render_init_py(context: ModuleTemplateContext) -> str:
    return (
        'from .module import register\n\n'
        '__all__ = ["register"]\n'
    )


def render_manifest_toml(context: ModuleTemplateContext) -> str:
    lines = [
        "[module]",
        f"module_id = {json.dumps(context.module_id)}",
        f"name = {json.dumps(context.display_name)}",
        'version = "0.1.0"',
        f"description = {json.dumps(context.description)}",
        f"author = {json.dumps(context.author)}",
        "",
    ]
    return "\n".join(lines)


def render_module_py(context: ModuleTemplateContext) -> str:
    return (
        "from __future__ import annotations\n\n"
        "from src.core.registry import ModuleMetadata\n\n"
        f"{context.class_name.upper()}_MODULE = ModuleMetadata(\n"
        f"    module_id={json.dumps(context.module_id)},\n"
        f"    name={json.dumps(context.display_name)},\n"
        '    version="0.1.0",\n'
        f"    description={json.dumps(context.description)},\n"
        ")\n\n\n"
        "def register(registry):\n"
        f"    registry.register_module({context.class_name.upper()}_MODULE)\n"
    )


def render_actions_py(context: ModuleTemplateContext) -> str:
    return (
        '"""Action descriptors for this module."""\n\n'
        "from __future__ import annotations\n\n"
        "# TODO: add action descriptors for this module.\n"
        "ACTION_DESCRIPTORS = []\n"
    )


def render_tools_py(context: ModuleTemplateContext) -> str:
    return (
        '"""Tool descriptors for this module."""\n\n'
        "from __future__ import annotations\n\n"
        "# TODO: add tool descriptors for this module.\n"
        "TOOL_DESCRIPTORS = []\n"
    )


def render_commands_py(context: ModuleTemplateContext) -> str:
    return (
        '"""Command descriptors for this module."""\n\n'
        "from __future__ import annotations\n\n"
        "# TODO: add command descriptors for this module.\n"
        "COMMAND_DESCRIPTORS = []\n"
    )


def render_views_py(context: ModuleTemplateContext) -> str:
    return (
        '"""View descriptors for this module."""\n\n'
        "from __future__ import annotations\n\n"
        "# TODO: add view descriptors for this module.\n"
        "VIEW_DESCRIPTORS = []\n"
    )


def render_readme_md(context: ModuleTemplateContext) -> str:
    return (
        f"# {context.display_name}\n\n"
        f"{context.description or 'A bundled Apmatia module.'}\n"
    )


def render_test_py(context: ModuleTemplateContext) -> str:
    return (
        "from __future__ import annotations\n\n"
        "def test_module_placeholder():\n"
        "    assert True\n"
    )
