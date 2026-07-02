"""Agent management library for CRUD operations on AI agents."""

from .agent_prompt import AgentPrompt, compile_agent_system_prompt, default_agent_prompt
from .models import Agent
from .repositories import AgentRepository
from .services import AgentService
from .module import AgentManager

try:
    from .sqlite_repositories import (
        SQLiteAgentRepository,
        SQLiteAgentManagementBundle,
        AgentManagementTables,
        SQLiteAgentPromptRepository,
        AgentPromptManagementTables,
    )
except ModuleNotFoundError:
    SQLiteAgentRepository = None
    SQLiteAgentManagementBundle = None
    AgentManagementTables = None
    SQLiteAgentPromptRepository = None
    AgentPromptManagementTables = None

__all__ = [
    "Agent",
    "AgentPrompt",
    "AgentManager",
    "AgentRepository",
    "AgentService",
    "compile_agent_system_prompt",
    "default_agent_prompt",
]

if SQLiteAgentRepository is not None:
    __all__.extend(
        [
            "SQLiteAgentRepository",
            "SQLiteAgentManagementBundle",
            "AgentManagementTables",
            "SQLiteAgentPromptRepository",
            "AgentPromptManagementTables",
        ]
    )
