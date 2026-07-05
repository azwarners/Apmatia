from __future__ import annotations

from apmatia.core.module_view_schema import build_collection_view_schema
from apmatia.core.registry import ViewContribution

from .models import AIHost

SSH_KEY_CONTAINER_PATH = "~/.apmatia/ssh/id_ed25519"
SSH_KEY_QUICKSTART = (
    "Need a new SSH key? On the machine running Apmatia, run "
    "`mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -t ed25519 -C \"apmatia-ai-host\" "
    "-f ~/.ssh/id_ed25519`."
)
SSH_KEY_PREP_COMMAND = (
    "mkdir -p ~/.apmatia/ssh && "
    "chmod 700 ~/.apmatia/ssh && "
    "ssh-keygen -t ed25519 -N \"\" -C \"apmatia-ai-host\" -f ~/.apmatia/ssh/id_ed25519"
)

HOST_VIEW_SCHEMA = build_collection_view_schema(
    AIHost,
    list_fields=("name", "hostname", "role", "connection_type", "username", "port", "credential_ref", "enabled", "notes"),
    create_fields=("name", "hostname", "role", "connection_type", "username", "port", "credential_ref", "enabled", "notes"),
    edit_fields=("name", "hostname", "role", "connection_type", "username", "port", "credential_ref", "enabled", "notes"),
    field_overrides={
        "id": {"hidden": True},
        "created_at": {"hidden": True},
        "updated_at": {"hidden": True},
        "name": {"label": "Name", "placeholder": "Local inference node"},
        "hostname": {"label": "Hostname", "placeholder": "localhost"},
        "role": {
            "label": "Role",
            "placeholder": "inference",
            "help_text": "A free-form label such as inference, training, or utility.",
        },
        "connection_type": {
            "label": "Connection type",
            "field_type": "select",
            "options": ["local", "ssh"],
            "default": "local",
            "help_text": "Choose ssh only if the host should be reached over the network with a private key path the Apmatia container can read.",
        },
        "username": {
            "label": "Username",
            "placeholder": "nick",
            "help_text": "SSH username for remote hosts. Leave blank for purely local records.",
        },
        "port": {
            "label": "Port",
            "min_value": 1,
            "max_value": 65535,
            "step": 1,
            "help_text": "SSH port or a placeholder value for local records.",
        },
        "credential_ref": {
            "label": "Credential ref",
            "placeholder": SSH_KEY_CONTAINER_PATH,
            "help_text": (
                "This is the private-key path the Apmatia container should use for SSH. "
                f"For SSH hosts, point it at the mounted path {SSH_KEY_CONTAINER_PATH}. "
                "Use the form action to generate or prepare that key path automatically when possible. "
                f"You can generate that mounted key path directly with: {SSH_KEY_PREP_COMMAND} "
                "and then set credential_ref to `~/.apmatia/ssh/id_ed25519`. "
                "Never store plaintext passwords here. "
                "Examples: `env:APMATIA_SSH_KEY` or `ssh-agent:workstation`."
            ),
        },
        "enabled": {"label": "Enabled"},
        "notes": {"field_type": "textarea", "help_text": "Optional operator notes."},
    },
    create={
        "title": "Add host",
        "description": (
            "Record a local or SSH AI-capable host without storing secrets. "
            f"For SSH, credential_ref is the private key path inside the container, usually {SSH_KEY_CONTAINER_PATH}. "
            "If you are creating an SSH host, use the Generate/Prepare SSH key action to create the mounted key path automatically before saving. "
            "If you already know the SSH password for the remote account, paste it once into SSH bootstrap password and Apmatia will try to install the generated public key automatically."
        ),
        "submit_label": "Save host",
        "cancel_label": "Cancel",
        "actions": [
            {
                "key": "prepare_ssh_key",
                "label": "Generate/Prepare SSH key",
                "intent": "prepare_ssh_key",
                "scope": "form",
                "style": "secondary",
                "payload": {"command_id": "apmatia_ai_host_management.hosts.prepare_ssh_key"},
            },
            {
                "key": "prepare_ssh_copy_command",
                "label": "Prepare SSH copy command",
                "intent": "prepare_ssh_copy_command",
                "scope": "form",
                "style": "secondary",
                "payload": {"command_id": "apmatia_ai_host_management.hosts.prepare_ssh_copy_command"},
            }
        ],
        "extra_fields": [
            {
                "key": "bootstrap_password",
                "label": "SSH bootstrap password",
                "field_type": "password",
                "default": "",
                "help_text": (
                    "Optional one-time password used to copy the generated public key to the remote SSH host. "
                    "Apmatia never stores it. Leave this blank if the key is already installed."
                ),
            }
        ],
    },
)

VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        view_id="apmatia_ai_host_management.hosts.view",
        name="AI Hosts View",
        description="Manage local and SSH host records for future model placement.",
        metadata={
            "ui": {
                "render_mode": "collection",
                "title": "AI Hosts",
                "caption": "Track AI-capable hosts for future model placement.",
                "empty_state": "No AI hosts have been recorded yet.",
                "item_key": "id",
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "hostname", "label": "Hostname"},
                    {"key": "role", "label": "Role"},
                    {"key": "connection_type", "label": "Connection"},
                    {"key": "username", "label": "Username"},
                    {"key": "port", "label": "Port"},
                    {"key": "credential_ref", "label": "Credential Ref"},
                    {"key": "enabled", "label": "Enabled"},
                ],
                "item_actions": [
                    {
                        "key": "edit",
                        "label": "Edit",
                        "intent": "edit",
                        "scope": "item",
                        "style": "secondary",
                        "payload": {"command_id": "apmatia_ai_host_management.hosts.edit"},
                    },
                    {
                        "key": "disable",
                        "label": "Disable",
                        "intent": "disable",
                        "scope": "item",
                        "style": "secondary",
                        "confirmation": True,
                        "payload": {"command_id": "apmatia_ai_host_management.hosts.disable"},
                    },
                    {
                        "key": "delete",
                        "label": "Delete",
                        "intent": "delete",
                        "scope": "item",
                        "style": "secondary",
                        "confirmation": True,
                        "payload": {"command_id": "apmatia_ai_host_management.hosts.delete"},
                    },
                ],
                "view_actions": [
                    {
                        "key": "create",
                        "label": "Add host",
                        "intent": "create",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"command_id": "apmatia_ai_host_management.hosts.create"},
                    }
                ],
                "commands": {
                    "create": "apmatia_ai_host_management.hosts.create",
                    "delete": "apmatia_ai_host_management.hosts.delete",
                    "edit": "apmatia_ai_host_management.hosts.edit",
                    "disable": "apmatia_ai_host_management.hosts.disable",
                    "list": "apmatia_ai_host_management.hosts.list",
                },
            },
            "schema": dict(HOST_VIEW_SCHEMA),
            "object_type": "ai_host",
            "singular_label": "AI Host",
            "plural_label": "AI Hosts",
            "empty_state": "No AI hosts have been recorded yet.",
        },
    ),
    ViewContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.resources",
        view_id="apmatia_ai_host_management.resources.view",
        name="AI Host Resources View",
        description="Review the current RAM, VRAM, and GPU utilization reported by each registered AI host.",
        metadata={
            "ui": {
                "render_mode": "collection",
                "title": "AI Host Resources",
                "caption": "Current resource utilization gathered from each registered AI-capable host.",
                "empty_state": "No AI hosts have been recorded yet.",
                "item_key": "host_id",
                "columns": [
                    {"key": "host_summary", "label": "Host"},
                    {"key": "resource_status", "label": "Status"},
                    {"key": "resource_summary", "label": "Resource Summary"},
                    {"key": "gpu_summary", "label": "GPU Summary"},
                    {"key": "collection_timestamp", "label": "Collected At"},
                ],
            },
            "schema": dict(HOST_VIEW_SCHEMA),
            "object_type": "ai_host",
            "singular_label": "AI Host",
            "plural_label": "AI Host Resources",
            "empty_state": "No AI hosts have been recorded yet.",
        },
    ),
)
