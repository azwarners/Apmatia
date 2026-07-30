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

from .collections import PARTICIPANT_VIEW_SPEC


# Discussion view presentation tree
_DISCUSSION_PRESENTATION = ViewComponent(
    component_id="discussion-page",
    component_type="page",
    properties={"title": "Discussion", "caption": "Choose an agent or view all chats, select a discussion, and send prompts."},
    children=(
        ViewComponent(
            component_id="discussion-controls-panel",
            component_type="panel",
            properties={"title": "Discussion controls"},
            children=(
                ViewComponent(
                    component_id="agent-selection",
                    component_type="columns",
                    properties={"columns": 2},
                    children=(
                        ViewComponent(
                            component_id="agent-select-field",
                            component_type="field",
                            properties={"label": "Agent", "field_type": "select", "binding_source": "agents", "binding_path": "items"},
                        ),
                        ViewComponent(
                            component_id="discussion-select-field",
                            component_type="field",
                            properties={"label": "Discussion", "field_type": "select", "binding_source": "discussions", "binding_path": "items"},
                        ),
                    ),
                ),
            ),
        ),
        ViewComponent(
            component_id="chat-roster-panel",
            component_type="panel",
            properties={"title": "Chat roster"},
            children=(
                ViewComponent(
                    component_id="participant-multiselect",
                    component_type="field",
                    properties={"label": "Chat targets", "field_type": "multiselect", "binding_source": "agents", "binding_path": "items"},
                ),
                ViewComponent(
                    component_id="save-participants-action",
                    component_type="actions",
                    properties={"label": "Save chat targets"},
                    action_keys=("save_participants",),
                ),
            ),
        ),
        ViewComponent(
            component_id="group-chat-panel",
            component_type="panel",
            properties={"title": "Group chat"},
            children=(
                ViewComponent(
                    component_id="chat-mode-select",
                    component_type="field",
                    properties={"label": "Mode", "field_type": "select", "options": ("single", "round_robin", "auto_paced", "continuous", "direct")},
                ),
                ViewComponent(
                    component_id="pause-toggle",
                    component_type="field",
                    properties={"label": "Pause between turns", "field_type": "checkbox"},
                ),
                ViewComponent(
                    component_id="pause-seconds-field",
                    component_type="field",
                    properties={"label": "Pause seconds", "field_type": "number", "min_value": 0.0, "step": 0.5},
                    visible_when=ViewCondition(operator="equals", operands=("auto_paced", "$state.chat_mode")),
                ),
                ViewComponent(
                    component_id="coordinator-select",
                    component_type="field",
                    properties={"label": "Coordinator", "field_type": "select", "binding_source": "agents", "binding_path": "items"},
                ),
                ViewComponent(
                    component_id="group-chat-actions",
                    component_type="actions",
                    properties={"actions": ("save_mode", "pause", "resume")},
                    action_keys=("save_mode", "pause", "resume"),
                ),
            ),
        ),
        ViewComponent(
            component_id="messages-section",
            component_type="panel",
            properties={"title": "Messages"},
            children=(
                ViewComponent(
                    component_id="message-history",
                    component_type="timeline",
                    binding=ViewBinding(source="messages", path="items"),
                    properties={"binding_source": "messages", "binding_path": "items"},
                    children=(
                        ViewComponent(
                            component_id="message-item",
                            component_type="message",
                            properties={"binding_source": "messages", "binding_path": "items"},
                            children=(
                                ViewComponent(
                                    component_id="message-text",
                                    component_type="text",
                                    properties={"binding_source": "messages", "binding_path": "text"},
                                ),
                                ViewComponent(
                                    component_id="message-attachments",
                                    component_type="actions",
                                    properties={"label": "Attachments"},
                                    action_keys=("edit_message", "delete_message"),
                                ),
                            ),
                        ),
                    ),
                ),
                ViewComponent(
                    component_id="live-activity",
                    component_type="status",
                    properties={"binding_source": "activity", "binding_path": "status"},
                    visible_when=ViewCondition(operator="truthy", operands=("$state.is_streaming",)),
                ),
                ViewComponent(
                    component_id="bulk-delete-toggle",
                    component_type="field",
                    properties={"label": "Show Bulk Delete", "field_type": "checkbox"},
                ),
                ViewComponent(
                    component_id="stop-action",
                    component_type="actions",
                    properties={"label": "Stop", "visible_when": "$state.is_streaming"},
                    action_keys=("stop_message",),
                ),
            ),
        ),
        ViewComponent(
            component_id="composer-panel",
            component_type="panel",
            properties={"title": "Message"},
            children=(
                ViewComponent(
                    component_id="message-input",
                    component_type="field",
                    properties={"label": "Message", "field_type": "textarea", "placeholder": "Write a message"},
                ),
                ViewComponent(
                    component_id="attachment-upload",
                    component_type="field",
                    properties={"label": "Screenshots or images", "field_type": "file", "accept": ("png", "jpg", "jpeg", "webp", "gif")},
                ),
                ViewComponent(
                    component_id="send-action",
                    component_type="actions",
                    properties={"label": "Send message"},
                    action_keys=("send_message",),
                ),
            ),
        ),
    ),
)

# Discussion view data sources
_DISCUSSION_DATA_SOURCES = (
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="list_agents",
        item_key="id",
        empty_text="No agents available. Create an agent first.",
    ),
    ViewDataSource(
        key="discussions",
        kind="collection",
        operation="discussion_tree",
        depends_on=("agents",),
        item_key="discussion_id",
        empty_text="No discussions available.",
    ),
    ViewDataSource(
        key="messages",
        kind="stream",
        operation="discussion_state",
        depends_on=("discussions",),
        refresh=ViewRefreshPolicy(
            mode="poll",
            interval_seconds=0.5,
            cursor_key="cursor",
            generation_key="generation",
            update_strategy="append",
            reject_stale=True,
        ),
    ),
    ViewDataSource(
        key="activity",
        kind="singleton",
        operation="discussion_activity",
        depends_on=("messages",),
    ),
    ViewDataSource(
        key="model_configs",
        kind="collection",
        operation="list_llm_configs",
        item_key="id",
    ),
)

# Discussion view state definitions
_DISCUSSION_STATE = (
    ViewStateDefinition(
        key="selected_agent_id",
        value_type="integer",
        scope="session",
        default=None,
    ),
    ViewStateDefinition(
        key="selected_discussion_id",
        value_type="string",
        scope="session",
        default=None,
    ),
    ViewStateDefinition(
        key="chat_mode",
        value_type="string",
        scope="view",
        default="round_robin",
    ),
    ViewStateDefinition(
        key="is_streaming",
        value_type="boolean",
        scope="view",
        default=False,
    ),
    ViewStateDefinition(
        key="is_chat_paused",
        value_type="boolean",
        scope="view",
        default=False,
    ),
    ViewStateDefinition(
        key="active_message_index",
        value_type="integer",
        scope="view",
        default=None,
    ),
    ViewStateDefinition(
        key="edit_target",
        value_type="object",
        scope="event",
        default=None,
    ),
    ViewStateDefinition(
        key="delete_target",
        value_type="object",
        scope="event",
        default=None,
    ),
)

# Discussion view actions
_DISCUSSION_ACTIONS = (
    ViewAction(
        key="send_message",
        intent="send_message",
        label="Send message",
        scope="form",
        command_id="discuss.message.send",
        payload={"prompt": "$state.message_input", "agent_id": "$state.selected_agent_id", "discussion_id": "$state.selected_discussion_id"},
        confirmation=False,
        prevent_duplicate_submission=True,
        success_effects=(
            ViewEffect(effect_type="refresh_source", target="messages"),
            ViewEffect(effect_type="set_state", target="is_streaming", value=True),
        ),
    ),
    ViewAction(
        key="stop_message",
        intent="stop_message",
        label="Stop",
        scope="view",
        command_id="discuss.message.stop",
        success_effects=(
            ViewEffect(effect_type="set_state", target="is_streaming", value=False),
            ViewEffect(effect_type="refresh_source", target="messages"),
        ),
    ),
    ViewAction(
        key="save_participants",
        intent="update_participants",
        label="Save chat targets",
        scope="view",
        command_id="discuss.discussion.update_participants",
        payload={"discussion_id": "$state.selected_discussion_id", "participant_ids": "$state.participant_selection"},
        success_effects=(
            ViewEffect(effect_type="refresh_view", target="discussions"),
            ViewEffect(effect_type="show_notification", value="Chat targets updated."),
        ),
    ),
    ViewAction(
        key="save_mode",
        intent="update_chat_mode",
        label="Save mode",
        scope="view",
        command_id="discuss.discussion.set_chat_mode",
        payload={"discussion_id": "$state.selected_discussion_id", "mode": "$state.chat_mode"},
        success_effects=(
            ViewEffect(effect_type="refresh_view", target="discussions"),
            ViewEffect(effect_type="show_notification", value="Chat mode updated."),
        ),
    ),
    ViewAction(
        key="pause",
        intent="pause_chat",
        label="Pause",
        scope="view",
        command_id="discuss.chat.pause",
        success_effects=(
            ViewEffect(effect_type="set_state", target="is_chat_paused", value=True),
            ViewEffect(effect_type="show_notification", value="Chat paused."),
        ),
    ),
    ViewAction(
        key="resume",
        intent="resume_chat",
        label="Resume",
        scope="view",
        command_id="discuss.chat.resume",
        success_effects=(
            ViewEffect(effect_type="set_state", target="is_chat_paused", value=False),
            ViewEffect(effect_type="show_notification", value="Chat resumed."),
        ),
    ),
    ViewAction(
        key="edit_message",
        intent="edit_message",
        label="Edit",
        scope="message",
        command_id="discuss.message.update",
        payload={"discussion_id": "$state.selected_discussion_id", "index": "$item.index", "text": "$state.edit_target.text"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="edit_target", value=None),
            ViewEffect(effect_type="refresh_source", target="messages"),
        ),
    ),
    ViewAction(
        key="delete_message",
        intent="delete_message",
        label="Delete",
        scope="message",
        command_id="discuss.message.delete",
        payload={"discussion_id": "$state.selected_discussion_id", "index": "$item.index"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="delete_target", value=None),
            ViewEffect(effect_type="refresh_source", target="messages"),
        ),
    ),
    ViewAction(
        key="open_discussion",
        intent="open_discussion",
        label="Open",
        scope="navigation",
        command_id="discuss.discussion.open",
        payload={"discussion_id": "$item.discussion_id"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_discussion_id", value="$item.discussion_id"),
            ViewEffect(effect_type="refresh_source", target="messages"),
        ),
    ),
    ViewAction(
        key="create_discussion",
        intent="create_discussion",
        label="Start a new discussion",
        scope="view",
        command_id="discuss.discussion.create",
        payload={"agent_id": "$state.selected_agent_id", "title": "New Discussion"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_discussion_id", value="$result.discussion_id"),
            ViewEffect(effect_type="refresh_source", target="discussions"),
        ),
    ),
)

# Discussion view effects
_DISCUSSION_EFFECTS = (
    ViewEffect(effect_type="start_polling", target="messages"),
    ViewEffect(effect_type="stop_polling", target="messages"),
    ViewEffect(effect_type="navigate", target="discuss.chat_targets.view"),
    ViewEffect(effect_type="show_notification", target="notification"),
)

# Discussion view refresh policy
_DISCUSSION_REFRESH_POLICY = ViewRefreshPolicy(
    mode="poll",
    interval_seconds=0.5,
    cursor_key="cursor",
    generation_key="generation",
    update_strategy="append",
    reject_stale=True,
    stop_when=ViewCondition(operator="equals", operands=(False, "$state.is_streaming")),
)

# Discussion view capabilities
_DISCUSSION_CAPABILITIES = (
    "can_send_message",
    "can_stop_message",
    "can_edit_message",
    "can_delete_message",
    "can_update_participants",
    "can_update_chat_mode",
    "can_pause_chat",
    "can_resume_chat",
    "can_create_discussion",
    "can_open_discussion",
)


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="discuss",
        action_id="discuss.chat_targets",
        view_id="discuss.chat_targets.view",
        name="Chat Targets View",
        description="Choose an agent or group, keep the active chat roster in one place, and resume discussions from the same screen.",
        metadata={
            "view_contract_ready": True,
            "object_type": PARTICIPANT_VIEW_SPEC.object_type,
            "singular_label": PARTICIPANT_VIEW_SPEC.singular_label,
            "plural_label": PARTICIPANT_VIEW_SPEC.plural_label,
            "empty_state": "No chat targets have been recorded yet.",
            "presentation": _DISCUSSION_PRESENTATION,
            "data_sources": _DISCUSSION_DATA_SOURCES,
            "state": _DISCUSSION_STATE,
            "actions": _DISCUSSION_ACTIONS,
            "effects": _DISCUSSION_EFFECTS,
            "refresh_policy": _DISCUSSION_REFRESH_POLICY,
            "capabilities": _DISCUSSION_CAPABILITIES,
            "required_renderer_capabilities": ("timeline", "message", "composer", "status", "navigation"),
        },
    ),
    ViewContribution(
        module_id="discuss",
        action_id="discuss.discussion",
        view_id="discuss.discussion.view",
        name="Discussion View",
        description="Choose an agent or view all chats, select a discussion, and send prompts through the discussion backend.",
        metadata={
            "view_contract_ready": True,
            "object_type": "discussion",
            "singular_label": "Discussion",
            "plural_label": "Discussions",
            "empty_state": "No discussions are available yet.",
            "presentation": _DISCUSSION_PRESENTATION,
            "data_sources": _DISCUSSION_DATA_SOURCES,
            "state": _DISCUSSION_STATE,
            "actions": _DISCUSSION_ACTIONS,
            "effects": _DISCUSSION_EFFECTS,
            "refresh_policy": _DISCUSSION_REFRESH_POLICY,
            "capabilities": _DISCUSSION_CAPABILITIES,
            "required_renderer_capabilities": ("timeline", "message", "composer", "status"),
        },
    ),
)
