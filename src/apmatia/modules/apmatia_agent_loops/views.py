from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS = [
    ViewContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.contacts",
        view_id="apmatia_agent_loops.contacts.view",
        name="Contacts",
        description="Agents and groups that can own loop tasks.",
        metadata={"object_type": "contact"},
    ),
    ViewContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.tasks",
        view_id="apmatia_agent_loops.tasks.view",
        name="Tasks",
        description="Recorded loop executions.",
        metadata={"object_type": "run"},
    ),
    ViewContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.workspace",
        view_id="apmatia_agent_loops.workspace.view",
        name="Workspace",
        description="Workspace files for the selected contact.",
        metadata={"object_type": "workspace"},
    ),
    ViewContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.knowledge",
        view_id="apmatia_agent_loops.knowledge.view",
        name="Knowledge",
        description="Knowledge files for the selected contact.",
        metadata={"object_type": "knowledge"},
    ),
]
