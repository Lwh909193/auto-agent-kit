"""AutoAgentKit — 生产级 AI Agent 工具包"""
__version__ = "0.2.0"

from auto_agent_kit.core.plan_mode import PlanMode, ExecutionPlan, PlanStep, StepStatus
from auto_agent_kit.core.error_reflection import ErrorReflection, ErrorCategory, RecoveryStrategy
from auto_agent_kit.core.tool_router import ToolRouter, ToolPhase
from auto_agent_kit.core.dashboard import Dashboard
from auto_agent_kit.core.access_control import AccessControl, PermissionLevel
from auto_agent_kit.core.mcp_server import MCPServer
from auto_agent_kit.core.plugin import Plugin, PluginManager, LoggingPlugin, MetricsPlugin
from auto_agent_kit.core.async_plan import AsyncPlanMode, AsyncStepResult, run_plan

__all__ = [
    "PlanMode", "ExecutionPlan", "PlanStep", "StepStatus",
    "ErrorReflection", "ErrorCategory", "RecoveryStrategy",
    "ToolRouter", "ToolPhase",
    "Dashboard",
    "AccessControl", "PermissionLevel",
    "MCPServer",
    "Plugin", "PluginManager", "LoggingPlugin", "MetricsPlugin",
    "AsyncPlanMode", "AsyncStepResult", "run_plan",
]
