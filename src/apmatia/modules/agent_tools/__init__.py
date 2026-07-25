"""Agent tool definitions, assignment, and safe execution."""

from .executor import ToolExecutor, validate_json_schema
from .models import AgentToolAssignment, ToolCall, ToolDefinition, ToolResult
from .manager import ToolManager
from .registry import FunctionTool, ToolProvider, ToolRegistry, builtin_tool_definitions, register_builtin_tools
from .repositories import AgentToolAssignmentRepository, ToolDefinitionRepository
from .workspace_files import build_workspace_file_tool_providers, workspace_file_tool_definitions
from .workspace_modules import build_workspace_module_tool_providers, workspace_module_tool_definitions
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
    "build_workspace_module_tool_providers",
    "build_workspace_file_tool_providers",
    "register_builtin_tools",
    "workspace_file_tool_definitions",
    "workspace_module_tool_definitions",
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
