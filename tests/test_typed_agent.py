"""TypedAgent — 类型安全测试"""
import sys, os, json, dataclasses
from enum import Enum
from typing import Any, Optional, Literal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_agent_kit import (
    TypedTool, TypedToolDef, TypedAgent, AgentConfig,
    StructuredOutput,
    validate_type, coerce_type, get_json_schema_from_type,
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")

# ============ 1. 类型校验 ============
print("\n=== 1. 类型校验 ===")

test("str 校验通过", validate_type("hello", str)[0])
test("str 校验失败", not validate_type(123, str)[0])
test("int 校验通过", validate_type(42, int)[0])
test("int 校验失败", not validate_type("abc", int)[0])
test("float 校验通过", validate_type(3.14, float)[0])
test("float 接受 int", validate_type(42, float)[0])
test("bool 校验通过", validate_type(True, bool)[0])
test("bool 拒绝 int", not validate_type(1, bool)[0])
test("list 校验通过", validate_type([1, 2, 3], list)[0])
test("list 校验失败", not validate_type("abc", list)[0])
test("Any 总是通过", validate_type("anything", Any)[0])
test("None 校验通过", validate_type(None, Optional[str])[0])
test("None 非空校验", validate_type("x", Optional[str])[0])

# ============ 2. 类型转换 ============
print("\n=== 2. 类型转换 ===")

test("str->int", coerce_type("42", int) == 42)
test("float->int", coerce_type(3.14, int) == 3)
test("int->float", coerce_type(42, float) == 42.0)
test("str->float", coerce_type("3.14", float) == 3.14)
test("int->str", coerce_type(42, str) == "42")
test("str->bool true", coerce_type("true", bool) == True)
test("str->bool false", coerce_type("false", bool) == False)
test("None 保持 None", coerce_type(None, Optional[str]) is None)

# ============ 3. JSON Schema 生成 ============
print("\n=== 3. JSON Schema 生成 ===")

test("str schema", get_json_schema_from_type(str) == {"type": "string"})
test("int schema", get_json_schema_from_type(int) == {"type": "integer"})
test("float schema", get_json_schema_from_type(float) == {"type": "number"})
test("bool schema", get_json_schema_from_type(bool) == {"type": "boolean"})
test("list schema", get_json_schema_from_type(list[str])["type"] == "array")
test("dict schema", get_json_schema_from_type(dict)["type"] == "object")

# ============ 4. TypedTool 装饰器 ============
print("\n=== 4. TypedTool 装饰器 ===")

@TypedTool.create("add", "加法工具")
def add(a: int, b: int) -> int:
    return a + b

test("工具名称", add.name == "add")
test("工具描述", add.description == "加法工具")
test("参数 schema", "a" in add.parameters["properties"])
test("必填参数", "a" in add.parameters["required"])
test("返回类型", add.return_type == int)

# ============ 5. TypedTool 调用 ============
print("\n=== 5. TypedTool 调用 ===")

test("正常调用", TypedTool.call(add, a=1, b=2) == 3)
test("字符串转 int", TypedTool.call(add, a="3", b="4") == 7)
test("float 转 int", TypedTool.call(add, a=1.5, b=2.5) == 3)

try:
    TypedTool.call(add, a="abc", b=2)
    test("类型错误", False)
except TypeError:
    test("类型错误", True)

try:
    TypedTool.call(add, a=1)
    test("缺少参数", False)
except TypeError:
    test("缺少参数", True)

# ============ 6. TypedTool validate_args ============
print("\n=== 6. TypedTool validate_args ===")

ok, msg, validated = TypedTool.validate_args(add, {"a": 1, "b": 2})
test("校验通过", ok)
test("校验值", validated == {"a": 1, "b": 2})

ok, msg, validated = TypedTool.validate_args(add, {"a": "3", "b": "4"})
test("校验+转换", ok and validated["a"] == 3)

ok, msg, validated = TypedTool.validate_args(add, {"a": 1})
test("缺少参数校验", not ok)

# ============ 7. TypedAgent 创建 ============
print("\n=== 7. TypedAgent 创建 ===")

agent = TypedAgent(AgentConfig(
    name="test_agent",
    model="deepseek",
    system_prompt="你是一个测试 Agent",
    temperature=0.5,
))

test("Agent 名称", agent.name == "test_agent")
test("Agent 模型", agent.config.model == "deepseek")
test("Agent 温度", agent.config.temperature == 0.5)
test("初始工具数", len(agent.list_tools()) == 0)

# ============ 8. TypedAgent 工具注册 ============
print("\n=== 8. TypedAgent 工具注册 ===")

@agent.tool("multiply", "乘法工具")
def multiply(x: int, y: int) -> int:
    return x * y

test("注册后工具数", len(agent.list_tools()) == 1)
test("获取工具", agent.get_tool("multiply") is not None)
test("工具名称", agent.get_tool("multiply").name == "multiply")

# ============ 9. TypedAgent 工具调用 ============
print("\n=== 9. TypedAgent 工具调用 ===")

test("Agent 调用工具", agent.call_tool("multiply", x=3, y=4) == 12)
test("Agent 调用带转换", agent.call_tool("multiply", x="5", y="6") == 30)

try:
    agent.call_tool("multiply", x="abc", y=2)
    test("Agent 类型错误", False)
except TypeError:
    test("Agent 类型错误", True)

try:
    agent.call_tool("nonexistent", x=1, y=2)
    test("Agent 不存在工具", False)
except ValueError:
    test("Agent 不存在工具", True)

# ============ 10. 系统提示词 ============
print("\n=== 10. 系统提示词 ===")

prompt = agent.build_system_prompt()
test("提示词含系统消息", "测试 Agent" in prompt)
test("提示词含工具", "multiply" in prompt)

# ============ 11. MCP 导出 ============
print("\n=== 11. MCP 导出 ===")

mcp_tools = agent.to_mcp_tools()
test("MCP 工具列表", len(mcp_tools) == 1)
test("MCP 工具名称", mcp_tools[0]["name"] == "multiply")
test("MCP 工具参数", "parameters" in mcp_tools[0])

# ============ 12. 多工具注册 ============
print("\n=== 12. 多工具注册 ===")

@agent.tool("concat", "字符串拼接")
def concat(a: str, b: str) -> str:
    return a + b

@agent.tool()
def greet(name: str) -> str:
    """问候工具"""
    return f"Hello, {name}!"

test("多工具注册", len(agent.list_tools()) == 3)
test("默认名称", agent.get_tool("greet") is not None)
test("默认描述", "问候工具" in agent.get_tool("greet").description)

# ============ 13. StructuredOutput ============
print("\n=== 13. StructuredOutput ===")

@dataclasses.dataclass
class AnalysisResult:
    title: str
    score: float
    tags: list[str]
    is_valid: bool

test("创建结构化输出", StructuredOutput.create(AnalysisResult) is AnalysisResult)

# 解析 JSON
json_str = '{"title": "测试", "score": 95.5, "tags": ["AI", "ML"], "is_valid": true}'
result = StructuredOutput.parse_json(json_str, AnalysisResult)
test("JSON 解析", result.title == "测试")
test("JSON 解析分数", result.score == 95.5)
test("JSON 解析标签", result.tags == ["AI", "ML"])
test("JSON 解析布尔", result.is_valid == True)

# 提示词生成
prompt = StructuredOutput.format_prompt(AnalysisResult, "请分析结果")
test("提示词含描述", "请分析结果" in prompt)
test("提示词含 schema", "score" in prompt)
test("提示词含 JSON", "```json" in prompt)

# schema 转 JSON
schema_json = StructuredOutput.schema_to_json(AnalysisResult)
test("schema JSON", "score" in schema_json)
test("schema JSON 可解析", isinstance(json.loads(schema_json), dict))

# ============ 14. Enum 类型 ============
print("\n=== 14. Enum 类型 ===")

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

test("Enum 校验", validate_type("active", Status)[0])
test("Enum 无效值", not validate_type("unknown", Status)[0])
test("Enum 对象校验", validate_type(Status.ACTIVE, Status)[0])

# ============ 15. Literal 类型 ============
print("\n=== 15. Literal 类型 ===")

test("Literal 校验", validate_type("high", Literal["low", "medium", "high"])[0])
test("Literal 无效", not validate_type("unknown", Literal["low", "medium"])[0])

# ============ 16. dataclass 参数 ============
print("\n=== 16. dataclass 参数 ===")

@dataclasses.dataclass
class Config:
    host: str = "localhost"
    port: int = 8080

@TypedTool.create("setup")
def setup(config: Config) -> str:
    return f"Config: {config.host}:{config.port}"

test("dataclass 参数 schema", "config" in setup.parameters["properties"])
test("dataclass 默认值", "port" not in setup.parameters.get("required", []))

# ============ 17. 无注解参数 ============
print("\n=== 17. 无注解参数 ===")

@TypedTool.create("echo")
def echo(msg):
    return msg

test("无注解参数", echo.parameters["properties"]["msg"]["type"] == "string")

# ============ 18. 复杂类型 ============
print("\n=== 18. 复杂类型 ===")

@TypedTool.create("process_items")
def process_items(items: list[str], count: int) -> list[str]:
    return items[:count]

test("复杂参数", TypedTool.call(process_items, items=["a", "b", "c"], count=2) == ["a", "b"])
test("类型转换", TypedTool.call(process_items, items=["a", "b", "c"], count="2") == ["a", "b"])

# ============ 19. AgentConfig 默认值 ============
print("\n=== 19. AgentConfig 默认值 ===")

default_config = AgentConfig()
test("默认名称", default_config.name == "agent")
test("默认模型", default_config.model == "default")
test("默认温度", default_config.temperature == 0.7)
test("默认重试", default_config.retry_count == 3)

# ============ 20. 空 Agent ============
print("\n=== 20. 空 Agent ===")

empty_agent = TypedAgent()
test("空 Agent 名称", empty_agent.name == "agent")
test("空 Agent 工具数", len(empty_agent.list_tools()) == 0)
test("空 Agent 提示词", empty_agent.build_system_prompt() == "")
test("空 Agent MCP", empty_agent.to_mcp_tools() == [])

# ============ 总结 ============
print(f"\n{'='*40}")
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 测试")
print(f"{'='*40}")

sys.exit(0 if failed == 0 else 1)
