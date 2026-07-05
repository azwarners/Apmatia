from __future__ import annotations

from apmatia.core.registry import CommandContribution

HOST_VIEW_ID = "apmatia_ai_host_management.hosts.view"


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.list",
        path=("apmatia_ai_host_management", "hosts", "list"),
        name="AI Hosts List",
        description="List all configured AI hosts.",
        metadata={"object_type": "ai_host", "verb": "list", "collection_view_id": HOST_VIEW_ID},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.create",
        path=("apmatia_ai_host_management", "hosts", "create"),
        name="AI Hosts Create",
        description="Create an AI host record.",
        metadata={"object_type": "ai_host", "verb": "create", "collection_view_id": HOST_VIEW_ID},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.edit",
        path=("apmatia_ai_host_management", "hosts", "edit"),
        name="AI Hosts Edit",
        description="Edit an AI host record.",
        metadata={"object_type": "ai_host", "verb": "edit", "collection_view_id": HOST_VIEW_ID},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.disable",
        path=("apmatia_ai_host_management", "hosts", "disable"),
        name="AI Hosts Disable",
        description="Disable an AI host record.",
        metadata={"object_type": "ai_host", "verb": "disable", "collection_view_id": HOST_VIEW_ID},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.delete",
        path=("apmatia_ai_host_management", "hosts", "delete"),
        name="AI Hosts Delete",
        description="Delete an AI host record.",
        metadata={"object_type": "ai_host", "verb": "delete", "collection_view_id": HOST_VIEW_ID},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.resources",
        command_id="apmatia_ai_host_management.resources.inspect_local",
        path=("apmatia_ai_host_management", "resources", "inspect_local"),
        name="Inspect AI Host Resources",
        description="Inspect current RAM, VRAM, and GPU utilization for registered AI hosts.",
        metadata={"object_type": "host_resources", "verb": "inspect"},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.resources",
        command_id="apmatia_ai_host_management.resources.validate",
        path=("apmatia_ai_host_management", "resources", "validate"),
        name="Validate Host Configuration",
        description="Validate a proposed host record without storing it.",
        metadata={"object_type": "host_resources", "verb": "validate"},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.prepare_ssh_key",
        path=("apmatia_ai_host_management", "hosts", "prepare_ssh_key"),
        name="Prepare SSH Key",
        description="Generate or prepare the SSH key path used by host records.",
        metadata={"object_type": "ai_host", "verb": "prepare_ssh_key"},
    ),
    CommandContribution(
        module_id="apmatia_ai_host_management",
        action_id="apmatia_ai_host_management.hosts",
        command_id="apmatia_ai_host_management.hosts.prepare_ssh_copy_command",
        path=("apmatia_ai_host_management", "hosts", "prepare_ssh_copy_command"),
        name="Prepare SSH Copy Command",
        description="Generate the command used to install the public key on the remote AI host.",
        metadata={"object_type": "ai_host", "verb": "prepare_ssh_copy_command"},
    ),
)
