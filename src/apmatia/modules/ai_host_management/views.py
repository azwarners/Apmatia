from __future__ import annotations

from apmatia.core.registry import ViewContribution
from apmatia.core.view_contract.models import (
    ViewComponent,
    ViewBinding,
    ViewCondition,
    ViewDataSource,
    ViewStateDefinition,
    ViewAction,
    ViewEffect,
    ViewRefreshPolicy,
)

from .models import AIHost

SSH_KEY_CONTAINER_PATH = "~/.apmatia/ssh/id_ed25519"
SSH_KEY_PREP_COMMAND = (
    "mkdir -p ~/.apmatia/ssh && "
    "chmod 700 ~/.apmatia/ssh && "
    "ssh-keygen -t ed25519 -N \"\" -C \"apmatia-ai-host\" -f ~/.apmatia/ssh/id_ed25519"
)

# AI Host form fields
_AI_HOST_FORM_FIELDS = (
    ViewComponent(
        component_id="ai-host-name-field",
        component_type="field",
        properties={"label": "Name", "field_type": "text", "placeholder": "Local inference node"},
    ),
    ViewComponent(
        component_id="ai-host-hostname-field",
        component_type="field",
        properties={"label": "Hostname", "field_type": "text", "placeholder": "localhost"},
    ),
    ViewComponent(
        component_id="ai-host-role-field",
        component_type="field",
        properties={"label": "Role", "field_type": "text", "placeholder": "inference", "help_text": "A free-form label such as inference, training, or utility."},
    ),
    ViewComponent(
        component_id="ai-host-connection-type-field",
        component_type="field",
        properties={"label": "Connection type", "field_type": "select", "options": ("local", "ssh"), "default": "local", "help_text": "Choose ssh only if the host should be reached over the network with a private key path the Apmatia container can read."},
    ),
    ViewComponent(
        component_id="ai-host-username-field",
        component_type="field",
        properties={"label": "Username", "field_type": "text", "placeholder": "nick", "help_text": "SSH username for remote hosts. Leave blank for purely local records."},
    ),
    ViewComponent(
        component_id="ai-host-port-field",
        component_type="field",
        properties={"label": "Port", "field_type": "number", "min_value": 1, "max_value": 65535, "step": 1, "help_text": "SSH port or a placeholder value for local records."},
    ),
    ViewComponent(
        component_id="ai-host-credential-ref-field",
        component_type="field",
        properties={"label": "Credential ref", "field_type": "text", "placeholder": SSH_KEY_CONTAINER_PATH, "help_text": f"This is the private-key path the Apmatia container should use for SSH. For SSH hosts, point it at the mounted path {SSH_KEY_CONTAINER_PATH}. Use the form action to generate or prepare that key path automatically when possible. You can generate that mounted key path directly with: {SSH_KEY_PREP_COMMAND} and then set credential_ref to ~/.apmatia/ssh/id_ed25519. Never store plaintext passwords here. Examples: env:APMATIA_SSH_KEY or ssh-agent:workstation."},
    ),
    ViewComponent(
        component_id="ai-host-enabled-field",
        component_type="field",
        properties={"label": "Enabled", "field_type": "checkbox", "default": True},
    ),
    ViewComponent(
        component_id="ai-host-notes-field",
        component_type="field",
        properties={"label": "Notes", "field_type": "textarea", "help_text": "Optional operator notes."},
    ),
    ViewComponent(
        component_id="ai-host-bootstrap-password-field",
        component_type="field",
        properties={"label": "SSH bootstrap password", "field_type": "password", "help_text": "Optional one-time password used to copy the generated public key to the remote SSH host. Apmatia never stores it. Leave this blank if the key is already installed."},
    ),
)

# AI Hosts view presentation tree
_AI_HOSTS_PRESENTATION = ViewComponent(
    component_id="ai-hosts-page",
    component_type="page",
    properties={"title": "AI Hosts", "caption": "Track AI-capable hosts for future model placement."},
    children=(
        ViewComponent(
            component_id="ai-hosts-collection",
            component_type="collection",
            binding=ViewBinding(source="ai_hosts", path="items"),
            children=(
                ViewComponent(
                    component_id="ai-hosts-table",
                    component_type="table",
                    properties={
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
                    },
                    action_keys=("edit", "disable", "delete"),
                ),
            ),
        ),
        ViewComponent(
            component_id="ai-hosts-view-actions",
            component_type="actions",
            properties={"label": "Add host"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-ai-host-form",
            component_type="form",
            properties={"title": "Add host", "submit_label": "Save host"},
            children=_AI_HOST_FORM_FIELDS,
            action_keys=("create", "prepare_ssh_key", "prepare_ssh_copy_command"),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-ai-host-form",
            component_type="form",
            properties={"title": "Edit host", "submit_label": "Save host"},
            children=_AI_HOST_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# AI Hosts view data sources
_AI_HOSTS_DATA_SOURCES = (
    ViewDataSource(
        key="ai_hosts",
        kind="collection",
        operation="ai_host_management.hosts:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed host", "include_empty": True},
    ),
)

# AI Hosts view state
_AI_HOSTS_STATE = (
    ViewStateDefinition(key="selected_host_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# AI Hosts view actions
_AI_HOSTS_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Add host",
        scope="view",
        style="primary",
        operation="ai_host_management.hosts:create",
        payload={"command_id": "ai_host_management.hosts.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="ai_host_management.hosts.view"),
            ViewEffect(effect_type="show_notification", value="Host added successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        style="secondary",
        operation="ai_host_management.hosts:edit",
        payload={"command_id": "ai_host_management.hosts.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_host_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="ai_host_management.hosts.view"),
        ),
    ),
    ViewAction(
        key="disable",
        intent="disable",
        label="Disable",
        scope="item",
        style="secondary",
        operation="ai_host_management.hosts:disable",
        payload={"command_id": "ai_host_management.hosts.disable"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="refresh_view", target="ai_host_management.hosts.view"),
            ViewEffect(effect_type="show_notification", value="Host disabled"),
        ),
    ),
    ViewAction(
        key="delete",
        intent="delete",
        label="Delete",
        scope="item",
        style="secondary",
        operation="ai_host_management.hosts:delete",
        payload={"command_id": "ai_host_management.hosts.delete"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_host_id", value=""),
            ViewEffect(effect_type="refresh_view", target="ai_host_management.hosts.view"),
            ViewEffect(effect_type="show_notification", value="Host deleted"),
        ),
    ),
    ViewAction(
        key="prepare_ssh_key",
        intent="prepare_ssh_key",
        label="Generate/Prepare SSH key",
        scope="form",
        style="secondary",
        operation="ai_host_management.hosts:prepare_ssh_key",
        payload={"command_id": "ai_host_management.hosts.prepare_ssh_key"},
        success_effects=(
            ViewEffect(effect_type="show_notification", value="SSH key prepared"),
        ),
    ),
    ViewAction(
        key="prepare_ssh_copy_command",
        intent="prepare_ssh_copy_command",
        label="Prepare SSH copy command",
        scope="form",
        style="secondary",
        operation="ai_host_management.hosts:prepare_ssh_copy_command",
        payload={"command_id": "ai_host_management.hosts.prepare_ssh_copy_command"},
        success_effects=(
            ViewEffect(effect_type="show_notification", value="SSH copy command prepared"),
        ),
    ),
)

# AI Hosts view effects
_AI_HOSTS_EFFECTS = ()

# AI Hosts view refresh policy
_AI_HOSTS_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")

# AI Host Resources view presentation tree (simplified for read-only)
_AI_HOST_RESOURCES_PRESENTATION = ViewComponent(
    component_id="ai-host-resources-page",
    component_type="page",
    properties={"title": "AI Host Resources", "caption": "Current resource utilization gathered from each registered AI-capable host."},
    children=(
        ViewComponent(
            component_id="ai-host-resources-collection",
            component_type="collection",
            binding=ViewBinding(source="host_resources", path="items"),
            children=(
                ViewComponent(
                    component_id="ai-host-resources-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "host_summary", "label": "Host"},
                            {"key": "resource_status", "label": "Status"},
                            {"key": "resource_summary", "label": "Resource Summary"},
                            {"key": "resource_error", "label": "Resource Error"},
                            {"key": "troubleshooting_hint", "label": "Troubleshooting"},
                            {"key": "ssh_connection_test_command", "label": "SSH Test"},
                            {"key": "ssh_public_key_install_command", "label": "SSH Key Install"},
                            {"key": "ssh_resource_probe_command", "label": "SSH Probe"},
                        ],
                    },
                ),
            ),
        ),
    ),
)

# AI Host Resources view data sources
_AI_HOST_RESOURCES_DATA_SOURCES = (
    ViewDataSource(
        key="host_resources",
        kind="collection",
        operation="ai_host_management.resources:list",
        parameters={"label_keys": ["host_summary"], "value_key": "host_id", "default_label": "Unnamed host", "include_empty": True},
    ),
)

# AI Host Resources view state
_AI_HOST_RESOURCES_STATE = ()

# AI Host Resources view actions
_AI_HOST_RESOURCES_ACTIONS = ()

# AI Host Resources view effects
_AI_HOST_RESOURCES_EFFECTS = ()

# AI Host Resources view refresh policy
_AI_HOST_RESOURCES_REFRESH_POLICY = ViewRefreshPolicy(mode="poll", interval_seconds=30.0)


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="ai_host_management",
        action_id="ai_host_management.hosts",
        view_id="ai_host_management.hosts.view",
        name="AI Hosts View",
        description="Manage local and SSH host records for future model placement.",
        metadata={
            "view_contract_ready": True,
            "object_type": "ai_host",
            "singular_label": "AI Host",
            "plural_label": "AI Hosts",
            "empty_state": "No AI hosts have been recorded yet.",
            "presentation": _AI_HOSTS_PRESENTATION,
            "data_sources": _AI_HOSTS_DATA_SOURCES,
            "state": _AI_HOSTS_STATE,
            "actions": _AI_HOSTS_ACTIONS,
            "effects": _AI_HOSTS_EFFECTS,
            "refresh_policy": _AI_HOSTS_REFRESH_POLICY,
        },
    ),
    ViewContribution(
        module_id="ai_host_management",
        action_id="ai_host_management.resources",
        view_id="ai_host_management.resources.view",
        name="AI Host Resources View",
        description="Review the current RAM, VRAM, and GPU utilization reported by each registered AI host.",
        metadata={
            "view_contract_ready": True,
            "object_type": "host_resource",
            "singular_label": "Host Resource",
            "plural_label": "Host Resources",
            "empty_state": "No AI hosts have been recorded yet.",
            "presentation": _AI_HOST_RESOURCES_PRESENTATION,
            "data_sources": _AI_HOST_RESOURCES_DATA_SOURCES,
            "state": _AI_HOST_RESOURCES_STATE,
            "actions": _AI_HOST_RESOURCES_ACTIONS,
            "effects": _AI_HOST_RESOURCES_EFFECTS,
            "refresh_policy": _AI_HOST_RESOURCES_REFRESH_POLICY,
        },
    ),
)
