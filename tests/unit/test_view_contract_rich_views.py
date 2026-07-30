from __future__ import annotations

from apmatia.core.view_contract import (
    RendererCapabilities,
    ViewAction,
    ViewBinding,
    ViewComponent,
    ViewCondition,
    ViewDataSource,
    ViewDocument,
    ViewEffect,
    ViewRefreshPolicy,
    ViewStateDefinition,
    negotiate_view_contract,
    validate_view_document,
)


def _discussion_document() -> ViewDocument:
    active_discussion = ViewBinding(source="active_discussion_id")
    return ViewDocument(
        view_id="discuss.conversation.view",
        module_id="discuss",
        title="Discussion",
        required_renderer_capabilities=("stream_updates", "file_input"),
        state=(
            ViewStateDefinition(key="active_contact_id", scope="session"),
            ViewStateDefinition(key="active_discussion_id", scope="session"),
            ViewStateDefinition(key="draft", scope="view"),
            ViewStateDefinition(key="message_generation", value_type="integer", default=0, scope="view"),
        ),
        data_sources=(
            ViewDataSource(key="contacts", operation="discuss.contacts"),
            ViewDataSource(
                key="messages",
                kind="stream",
                operation="discuss.messages",
                depends_on=("active_discussion_id",),
                refresh=ViewRefreshPolicy(
                    mode="stream",
                    cursor_key="message_id",
                    generation_key="message_generation",
                    update_strategy="append",
                ),
            ),
            ViewDataSource(
                key="activity",
                kind="singleton",
                operation="discuss.activity",
                depends_on=("active_discussion_id",),
                refresh=ViewRefreshPolicy(
                    mode="poll",
                    interval_seconds=0.5,
                    generation_key="message_generation",
                    stop_when=ViewCondition("equals", (ViewBinding("activity", "status"), "idle")),
                ),
            ),
        ),
        actions=(
            ViewAction(
                key="activate_contact",
                intent="select_contact",
                label="Open",
                scope="navigation",
                operation="discuss.open_contact",
                success_effects=(
                    ViewEffect("set_state", target="active_contact_id", source="result.contact_id"),
                    ViewEffect("set_state", target="active_discussion_id", source="result.discussion_id"),
                    ViewEffect("refresh_source", target="messages"),
                ),
            ),
            ViewAction(
                key="send_message",
                intent="send_message",
                label="Send",
                scope="form",
                operation="discuss.prompt",
                enabled_when=ViewCondition("truthy", (active_discussion,)),
                success_effects=(
                    ViewEffect("clear_state", target="draft"),
                    ViewEffect("start_polling", target="activity"),
                ),
            ),
            ViewAction(
                key="stop_generation",
                intent="stop_discussion",
                label="Stop",
                scope="view",
                operation="discuss.stop",
                success_effects=(ViewEffect("stop_polling", target="activity"),),
            ),
            ViewAction(key="edit_message", intent="edit", label="Edit", scope="message", operation="discuss.edit_message"),
            ViewAction(
                key="delete_message",
                intent="delete",
                label="Delete",
                scope="message",
                operation="discuss.delete_message",
                confirmation=True,
            ),
        ),
        presentation=ViewComponent(
            component_id="discussion-page",
            component_type="page",
            children=(
                ViewComponent(
                    component_id="contacts",
                    component_type="navigation",
                    binding=ViewBinding("contacts"),
                    action_keys=("activate_contact",),
                ),
                ViewComponent(
                    component_id="conversation",
                    component_type="stack",
                    children=(
                        ViewComponent(
                            component_id="messages",
                            component_type="timeline",
                            binding=ViewBinding("messages"),
                            children=(
                                ViewComponent(
                                    component_id="message-template",
                                    component_type="message",
                                    action_keys=("edit_message", "delete_message"),
                                ),
                            ),
                        ),
                        ViewComponent(component_id="activity", component_type="status", binding=ViewBinding("activity")),
                        ViewComponent(
                            component_id="composer",
                            component_type="composer",
                            binding=ViewBinding("draft"),
                            action_keys=("send_message", "stop_generation"),
                        ),
                    ),
                ),
            ),
        ),
    )


def _agent_loops_document() -> ViewDocument:
    running = ViewCondition("equals", (ViewBinding("tasks", "selected.status"), "running"))
    return ViewDocument(
        view_id="agent_loops.shell.view",
        module_id="agent_loops",
        title="Agent Loops",
        required_renderer_capabilities=("polling", "terminal_output"),
        state=(
            ViewStateDefinition(key="active_contact_id", scope="session"),
            ViewStateDefinition(key="active_task_id", scope="view"),
            ViewStateDefinition(key="active_tab", default="current", scope="view"),
            ViewStateDefinition(key="task_generation", value_type="integer", default=0, scope="view"),
        ),
        data_sources=(
            ViewDataSource(key="contacts", operation="agent_loops.contacts"),
            ViewDataSource(
                key="tasks",
                operation="agent_loops.tasks",
                depends_on=("active_contact_id",),
                refresh=ViewRefreshPolicy(
                    mode="poll",
                    interval_seconds=1.0,
                    generation_key="task_generation",
                    update_strategy="replace",
                    stop_when=ViewCondition("not_equals", (ViewBinding("tasks", "selected.status"), "running")),
                ),
            ),
            ViewDataSource(key="workspace", kind="tree", operation="agent_loops.workspace", depends_on=("active_contact_id",)),
            ViewDataSource(key="knowledge", kind="tree", operation="agent_loops.knowledge", depends_on=("active_contact_id",)),
        ),
        actions=(
            ViewAction(
                key="select_contact",
                intent="select_contact",
                label="Select",
                scope="navigation",
                operation="agent_loops.select_contact",
                success_effects=(ViewEffect("set_state", target="active_contact_id", source="result.contact_id"),),
            ),
            ViewAction(
                key="start_task",
                intent="start_task",
                label="Start task",
                scope="form",
                operation="agent_loops.start",
                success_effects=(
                    ViewEffect("set_state", target="active_task_id", source="result.task_id"),
                    ViewEffect("start_polling", target="tasks"),
                ),
            ),
            ViewAction(
                key="stop_task",
                intent="stop_task",
                label="Stop task",
                scope="item",
                operation="agent_loops.stop",
                enabled_when=running,
                confirmation=True,
                success_effects=(ViewEffect("refresh_source", target="tasks"),),
            ),
        ),
        presentation=ViewComponent(
            component_id="loops-page",
            component_type="page",
            children=(
                ViewComponent(
                    component_id="loop-contacts",
                    component_type="navigation",
                    binding=ViewBinding("contacts"),
                    action_keys=("select_contact",),
                ),
                ViewComponent(
                    component_id="loop-tabs",
                    component_type="tabs",
                    children=(
                        ViewComponent(
                            component_id="current-task",
                            component_type="panel",
                            children=(
                                ViewComponent(component_id="task-terminal", component_type="terminal", binding=ViewBinding("tasks", "selected.events")),
                                ViewComponent(component_id="task-progress", component_type="progress", binding=ViewBinding("tasks", "selected.progress")),
                                ViewComponent(component_id="task-checklist", component_type="checklist", binding=ViewBinding("tasks", "selected.checklist")),
                                ViewComponent(component_id="task-form", component_type="form", action_keys=("start_task",)),
                            ),
                        ),
                        ViewComponent(
                            component_id="history",
                            component_type="collection",
                            binding=ViewBinding("tasks"),
                            action_keys=("stop_task",),
                        ),
                        ViewComponent(component_id="workspace", component_type="tree", binding=ViewBinding("workspace")),
                        ViewComponent(component_id="knowledge", component_type="tree", binding=ViewBinding("knowledge")),
                    ),
                ),
            ),
        ),
    )


def test_discussion_requirements_validate_and_negotiate():
    document = _discussion_document()
    renderer = RendererCapabilities(
        renderer_id="reference",
        capabilities=frozenset({"stream_updates", "file_input"}),
    )

    assert validate_view_document(document) is document
    assert negotiate_view_contract(document, renderer).document is document


def test_agent_loops_requirements_validate_and_negotiate():
    document = _agent_loops_document()
    renderer = RendererCapabilities(
        renderer_id="reference",
        capabilities=frozenset({"polling", "terminal_output"}),
    )

    assert validate_view_document(document) is document
    assert negotiate_view_contract(document, renderer).document is document
