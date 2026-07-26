from __future__ import annotations

from apmatia.core.registry import ViewContribution


_FIELDS = [
    {
        "key": "llama_server_log_dir",
        "label": "llama.cpp log directory",
        "section": "Runtime",
        "help": "Directory containing llama.cpp server log files. Leave blank to use an environment override.",
    },
    {
        "key": "llama_server_executable_path",
        "label": "llama-server executable",
        "section": "Runtime",
        "help": "Path to the local llama-server binary used for execution.",
    },
    {
        "key": "llama_server_default_args",
        "label": "llama-server default args",
        "section": "Runtime",
        "type": "textarea",
        "help": "One argument per line. These are passed to every local launch.",
    },
    {
        "key": "gguf_directories",
        "label": "GGUF model libraries",
        "section": "Model Discovery",
        "type": "textarea",
        "help": "Use one directory per line or separate them with commas. The scanner recurses through each library.",
    },
    {
        "key": "auto_scan_gguf_directory",
        "label": "Auto-scan GGUF directories on save",
        "section": "Model Discovery",
        "type": "checkbox",
        "default": True,
        "help": "GGUF directories are rescanned immediately when preferences are saved.",
    },
    {
        "key": "workspace_root",
        "label": "Workspace root",
        "section": "Agent Roots",
        "help": "Base directory for agent workspace roots.",
    },
    {
        "key": "knowledge_root",
        "label": "Knowledge root",
        "section": "Agent Roots",
        "help": "Base directory for shared knowledge roots.",
    },
    {
        "key": "timezone",
        "label": "Alarm time zone",
        "section": "Time Zone",
        "type": "select",
        "default": "America/Phoenix",
        "options": ["America/Phoenix", "America/Denver", "America/Chicago", "America/New_York", "UTC"],
        "help": "America/Phoenix remains on standard time year-round.",
    },
    {
        "key": "theme",
        "label": "Theme",
        "section": "Appearance",
        "type": "select",
        "default": "dark",
        "options": ["dark", "light", "system"],
    },
    {"key": "font_family", "label": "Font family", "section": "Appearance", "default": "system-ui"},
    {
        "key": "accent_color",
        "label": "Accent color",
        "section": "Appearance",
        "type": "color",
        "default": "#ff6b6b",
    },
    {
        "key": "font_size",
        "label": "Font size",
        "section": "Appearance",
        "type": "slider",
        "default": 16,
        "min_value": 12,
        "max_value": 24,
        "step": 1,
    },
    {
        "key": "title_bar_height",
        "label": "Title bar height",
        "section": "Appearance",
        "type": "slider",
        "default": 56,
        "min_value": 40,
        "max_value": 96,
        "step": 1,
    },
    {
        "key": "title_bar_font_size",
        "label": "Title bar font size",
        "section": "Appearance",
        "type": "slider",
        "default": 20,
        "min_value": 12,
        "max_value": 40,
        "step": 1,
    },
    {
        "key": "terminal_background_color",
        "label": "Terminal background",
        "section": "Terminal",
        "type": "color",
        "default": "#000000",
    },
    {
        "key": "terminal_text_color",
        "label": "Terminal text",
        "section": "Terminal",
        "type": "color",
        "default": "#9dffad",
    },
    {
        "key": "terminal_border_color",
        "label": "Terminal border",
        "section": "Terminal",
        "default": "rgba(110, 255, 170, 0.35)",
        "help": "Any valid CSS color is accepted.",
    },
    {
        "key": "terminal_muted_color",
        "label": "Terminal muted text",
        "section": "Terminal",
        "default": "rgba(157, 255, 173, 0.72)",
    },
]


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="preferences",
        action_id="preferences.preferences",
        view_id="preferences.preferences.view",
        name="Preferences",
        description="Configure Apmatia through the local API. Changes stay on this machine.",
        metadata={
            "object_type": "preferences",
            "ui": {
                "render_mode": "form",
                "title": "Preferences",
                "caption": "Runtime, model discovery, roots, time zone, appearance, and terminal configuration.",
                "form": {
                    "key": "preferences",
                    "title": "Preferences",
                    "submit_label": "Save preferences",
                    "cancel_label": "",
                    "fields": _FIELDS,
                },
                "view_actions": [
                    {
                        "key": "save",
                        "label": "Save preferences",
                        "intent": "save",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"command_id": "preferences.save"},
                    }
                ],
            },
        },
    ),
)
