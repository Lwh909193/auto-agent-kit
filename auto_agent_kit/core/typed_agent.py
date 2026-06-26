"""TypedAgent — 类型安全的 Agent 定义

借鉴 Pydantic AI 的类型安全设计，为 AutoAgentKit 提供：
- TypedTool: 带类型注解的工具定义，自动参数校验
- TypedAgent: 类型安全的 Agent 定义（FastAPI 风格）
- StructuredOutput: 结构化输出模式
- 集成到 ToolRouter 做参数校验

纯 Python，零外部依赖（仅用 typing + dataclasses）。
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import logging
import re
import typing
from dataclasses import dataclass, field, fields as dataclass_fields
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, get_type_hints

logger = logging.getLogger("auto_agent_kit.typed_agent")

T = TypeVar("T")


# ============ 类型校验工具 ============

def validate_type(value: Any, expected_type: type) -> tuple[bool, str]:
    """校验值是否符合预期类型"""
    if expected_type is Any:
        return True, ""

    origin = typing.get_origin(expected_type)
    args = typing.get_args(expected_type)

    # Optional[X] 或 Union[X, None]
    if origin is typing.Union and type(None) in args:
        if value is None:
            return True, ""
        real_type = [a for a in args if a is not type(None)][0]
        return validate_type(value, real_type)

    # list[X]
    if origin is list:
        if not isinstance(value, list):
            return False, f"期望 list，得到 {type(value).__name__}"
        if args:
            for i, item in enumerate(value):
                ok, msg = validate_type(item, args[0])
                if not ok:
                    return False, f"列表第 {i} 项: {msg}"
        return True, ""

    # dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            return False, f"期望 dict，得到 {type(value).__name__}"
        return True, ""

    # Literal
    if origin is typing.Literal:
        valid_values = args
        if value not in valid_values:
            return False, f"值 {value!r} 不在允许值 {valid_values} 中"
        return True, ""

    # 基本类型
    if expected_type is int:
        if isinstance(value, bool):
            return False, "期望 int，得到 bool"
        return (isinstance(value, (int, float)), f"期望 int，得到 {type(value).__name__}")

    if expected_type is float:
        return (isinstance(value, (int, float)), f"期望 float，得到 {type(value).__name__}")

    if expected_type is str:
        return (isinstance(value, str), f"期望 str，得到 {type(value).__name__}")

    if expected_type is bool:
        return (isinstance(value, bool), f"期望 bool，得到 {type(value).__name__}")

    if expected_type is bytes:
        return (isinstance(value, bytes), f"期望 bytes，得到 {type(value).__name__}")

    # Enum
    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        if isinstance(value, expected_type):
            return True, ""
        # 字符串转 Enum
        if isinstance(value, str):
            try:
                expected_type(value)
                return True, ""
            except (ValueError, KeyError):
                valid = [e.value for e in expected_type]
                return False, f"'{value}' 不在有效值 {valid} 中"
        return False, f"期望 {expected_type.__name__}，得到 {type(value).__name__}"

    # dataclass
    if dataclasses.is_dataclass(expected_type):
        if isinstance(value, dict):
            try:
                expected_type(**value)
                return True, ""
            except Exception as e:
                return False, f"dataclass 校验失败: {e}"
        return (isinstance(value, expected_type), f"期望 {expected_type.__name__}，得到 {type(value).__name__}")

    # 普通类型
    if isinstance(expected_type, type):
        return (isinstance(value, expected_type), f"期望 {expected_type.__name__}，得到 {type(value).__name__}")

    return True, ""


def coerce_type(value: Any, expected_type: type) -> Any:
    """尝试将值转换为目标类型"""
    if value is None:
        return None

    origin = typing.get_origin(expected_type)
    args = typing.get_args(expected_type)

    # Optional[X]
    if origin is typing.Union and type(None) in args:
        real_type = [a for a in args if a is not type(None)][0]
        return coerce_type(value, real_type)

    # int
    if expected_type is int:
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return value
        return value

    # float
    if expected_type is float:
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value
        return value

    # str
    if expected_type is str:
        return str(value)

    # bool
    if expected_type is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "y")
        return bool(value)

    # Enum
    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        if isinstance(value, str):
            try:
                return expected_type(value)
            except (ValueError, KeyError):
                return value
        return value

    return value


def get_json_schema_from_type(t: type) -> dict:
    """从 Python 类型生成 JSON Schema"""
    origin = typing.get_origin(t)
    args = typing.get_args(t)

    if t is str:
        return {"type": "string"}
    if t is int:
        return {"type": "integer"}
    if t is float:
        return {"type": "number"}
    if t is bool:
        return {"type": "boolean"}
    if t is Any:
        return {}

    if origin is typing.Union and type(None) in args:
        real_type = [a for a in args if a is not type(None)][0]
        schema = get_json_schema_from_type(real_type)
        return schema

    if t is list or origin is list:
        item_schema = get_json_schema_from_type(args[0]) if args else {}
        return {"type": "array", "items": item_schema}

    if t is dict or origin is dict:
        return {"type": "object"}

    if origin is typing.Literal:
        return {"enum": list(args)}

    if isinstance(t, type) and issubclass(t, Enum):
        return {"type": "string", "enum": [e.value for e in t]}

    if dataclasses.is_dataclass(t):
        properties = {}
        required = []
        for f in dataclass_fields(t):
            field_schema = get_json_schema_from_type(f.type)
            field_schema["description"] = f.metadata.get("description", "")
            properties[f.name] = field_schema
            if not is_optional(f.type):
                required.append(f.name)
        return {"type": "object", "properties": properties, "required": required}

    return {}


def is_optional(t: type) -> bool:
    """检查类型是否为 Optional"""
    origin = typing.get_origin(t)
    args = typing.get_args(t)
    return origin is typing.Union and type(None) in args


# ============ TypedTool ============

@dataclass
class TypedToolDef:
    """类型安全的工具定义"""
    name: str
    description: str
    handler: Callable
    parameters: dict = field(default_factory=dict)
    return_type: Optional[type] = None
    type_hints: dict = field(default_factory=dict)

    def to_mcp_tool(self) -> dict:
        """转换为 MCP 工具格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class TypedTool:
    """类型安全的工具装饰器/定义器"""

    @staticmethod
    def create(name: str, description: str = "") -> Callable:
        """装饰器：将函数定义为类型安全工具"""
        def decorator(func: Callable) -> TypedToolDef:
            sig = inspect.signature(func)
            hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

            # 构建参数 schema
            properties = {}
            required = []
            for param_name, param in sig.parameters.items():
                if param_name == "self" or param_name == "cls":
                    continue
                param_type = hints.get(param_name, str)
                param_schema = get_json_schema_from_type(param_type)
                param_schema["description"] = param_name
                properties[param_name] = param_schema
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            return TypedToolDef(
                name=name,
                description=description or func.__doc__ or name,
                handler=func,
                parameters=parameters,
                return_type=hints.get("return"),
                type_hints=hints,
            )
        return decorator

    @staticmethod
    def validate_args(tool_def: TypedToolDef, args: dict) -> tuple[bool, str, dict]:
        """校验并转换工具参数"""
        validated = {}
        for param_name, param_schema in tool_def.parameters.get("properties", {}).items():
            if param_name not in args:
                if param_name in tool_def.parameters.get("required", []):
                    return False, f"缺少必填参数: {param_name}", {}
                continue

            value = args[param_name]
            expected_type = tool_def.type_hints.get(param_name, str)

            # 尝试类型转换
            coerced = coerce_type(value, expected_type)
            ok, msg = validate_type(coerced, expected_type)
            if not ok:
                return False, f"参数 '{param_name}' 校验失败: {msg}", {}

            validated[param_name] = coerced

        return True, "", validated

    @staticmethod
    def call(tool_def: TypedToolDef, **kwargs) -> Any:
        """调用类型安全工具（带校验）"""
        ok, msg, validated = TypedTool.validate_args(tool_def, kwargs)
        if not ok:
            raise TypeError(msg)
        return tool_def.handler(**validated)


# ============ TypedAgent ============

@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str = "agent"
    model: str = "default"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[TypedToolDef] = field(default_factory=list)
    retry_count: int = 3
    timeout_seconds: int = 60


class TypedAgent:
    """类型安全的 Agent 定义（FastAPI 风格）"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self._tools: dict[str, TypedToolDef] = {}

    @property
    def name(self) -> str:
        return self.config.name

    def tool(self, name: str = "", description: str = ""):
        """装饰器：注册类型安全工具"""
        def decorator(func):
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or tool_name
            tool_def = TypedTool.create(tool_name, tool_desc)(func)
            self._tools[tool_name] = tool_def
            self.config.tools.append(tool_def)
            return tool_def
        return decorator

    def get_tool(self, name: str) -> Optional[TypedToolDef]:
        return self._tools.get(name)

    def list_tools(self) -> list[TypedToolDef]:
        return list(self._tools.values())

    def call_tool(self, name: str, **kwargs) -> Any:
        """调用工具（带类型校验）"""
        tool_def = self._tools.get(name)
        if not tool_def:
            raise ValueError(f"工具 '{name}' 未注册")
        return TypedTool.call(tool_def, **kwargs)

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        parts = [self.config.system_prompt] if self.config.system_prompt else []
        if self._tools:
            parts.append("\n可用工具：")
            for t in self._tools.values():
                parts.append(f"- {t.name}: {t.description}")
        return "\n".join(parts)

    def to_mcp_tools(self) -> list[dict]:
        """导出为 MCP 工具列表"""
        return [t.to_mcp_tool() for t in self._tools.values()]


# ============ StructuredOutput ============

class StructuredOutput:
    """结构化输出模式"""

    @staticmethod
    def create(schema: type) -> type:
        """从 dataclass 创建结构化输出模式"""
        if not dataclasses.is_dataclass(schema):
            raise TypeError("schema 必须是 dataclass")
        return schema

    @staticmethod
    def parse_json(json_str: str, schema: type[T]) -> T:
        """从 JSON 字符串解析为结构化输出"""
        data = json.loads(json_str)
        if dataclasses.is_dataclass(schema):
            return schema(**data)
        return data

    @staticmethod
    def format_prompt(schema: type, description: str = "") -> str:
        """生成结构化输出的提示词"""
        if not dataclasses.is_dataclass(schema):
            return description

        parts = [description] if description else []
        parts.append("\n请以 JSON 格式输出，严格按照以下 schema：")
        parts.append("```json")
        parts.append(json.dumps(get_json_schema_from_type(schema), ensure_ascii=False, indent=2))
        parts.append("```")

        return "\n".join(parts)

    @staticmethod
    def schema_to_json(schema: type) -> str:
        """将 schema 转换为 JSON 字符串"""
        return json.dumps(get_json_schema_from_type(schema), ensure_ascii=False, indent=2)
