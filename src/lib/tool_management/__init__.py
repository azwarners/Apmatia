"""Tool management library for Apmatia agents."""

from .executor import ToolExecutor, validate_json_schema
from .models import AgentToolAssignment, ToolCall, ToolDefinition, ToolResult
from .module import ToolManager
from .registry import FunctionTool, ToolProvider, ToolRegistry, builtin_tool_definitions, register_builtin_tools
from .repositories import AgentToolAssignmentRepository, ToolDefinitionRepository
from .services import ToolService

try:
    from .sqlite_repositories import (
        SQLiteAgentToolAssignmentRepository,
        SQLiteToolDefinitionRepository,
        SQLiteToolManagementBundle,
        ToolManagementTables,
    )
except ModuleNotFoundError:
    SQLiteAgentToolAssignmentRepository = None
    SQLiteToolDefinitionRepository = None
    SQLiteToolManagementBundle = None
    ToolManagementTables = None

__all__ = [
    "AgentToolAssignment",
    "AgentToolAssignmentRepository",
    "FunctionTool",
    "ToolCall",
    "ToolDefinition",
    "ToolDefinitionRepository",
    "ToolExecutor",
    "ToolManager",
    "ToolProvider",
    "ToolRegistry",
    "ToolResult",
    "ToolService",
    "builtin_tool_definitions",
    "register_builtin_tools",
    "validate_json_schema",
]

if SQLiteToolDefinitionRepository is not None:
    __all__.extend(
        [
            "SQLiteAgentToolAssignmentRepository",
            "SQLiteToolDefinitionRepository",
            "SQLiteToolManagementBundle",
            "ToolManagementTables",
        ]
    )
