"""AutoAgentKit — 生产级 AI Agent 工具包"""
__version__ = "0.4.2"

from auto_agent_kit.core.plan_mode import PlanMode, ExecutionPlan, PlanStep, StepStatus
from auto_agent_kit.core.error_reflection import ErrorReflection, ErrorCategory, RecoveryStrategy
from auto_agent_kit.core.tool_router import ToolRouter, ToolPhase
from auto_agent_kit.core.dashboard import Dashboard
from auto_agent_kit.core.access_control import AccessControl, PermissionLevel
from auto_agent_kit.core.mcp_server import MCPServer
from auto_agent_kit.core.plugin import Plugin, PluginManager, LoggingPlugin, MetricsPlugin
from auto_agent_kit.core.async_plan import AsyncPlanMode, AsyncStepResult, run_plan
from auto_agent_kit.core.context_compressor import ContextCompressor, CompressionState
from auto_agent_kit.core.task_lock import TaskLock, LockInfo, LockError
from auto_agent_kit.core.typed_agent import (
    TypedTool, TypedToolDef, TypedAgent, AgentConfig,
    StructuredOutput,
    validate_type, coerce_type, get_json_schema_from_type,
)
from auto_agent_kit.core.crew_role import (
    Crew, Role, Task as CrewTask, CrewResult,
    ProcessType,
)
from auto_agent_kit.core.state_graph import (
    StateGraph, CompiledGraph, GraphNode, GraphEdge, Checkpoint,
    NodeType, EdgeType,
    create_sequential_workflow, create_agent_loop, create_branching_workflow
)

__all__ = [
    "PlanMode", "ExecutionPlan", "PlanStep", "StepStatus",
    "ErrorReflection", "ErrorCategory", "RecoveryStrategy",
    "ToolRouter", "ToolPhase",
    "Dashboard",
    "AccessControl", "PermissionLevel",
    "MCPServer",
    "Plugin", "PluginManager", "LoggingPlugin", "MetricsPlugin",
    "AsyncPlanMode", "AsyncStepResult", "run_plan",
    "ContextCompressor", "CompressionState",
    "TaskLock", "LockInfo", "LockError",
    "StateGraph", "CompiledGraph", "GraphNode", "GraphEdge", "Checkpoint",
    "NodeType", "EdgeType",
    "create_sequential_workflow", "create_agent_loop", "create_branching_workflow",
    "Crew", "Role", "CrewTask", "CrewResult",
    "ProcessType",
    "TypedTool", "TypedToolDef", "TypedAgent", "AgentConfig",
    "StructuredOutput",
    "validate_type", "coerce_type", "get_json_schema_from_type",
]
