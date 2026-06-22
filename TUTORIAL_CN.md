# AutoAgentKit 实战教程：从零搭建你的 AI Agent 工具包

> 让你的 AI 拥有计划、反思、路由、监控、安全和通信能力

## 为什么需要 AutoAgentKit？

2026 年是智能体爆发年。但大多数 AI Agent 项目都面临同一个问题：**从零搭建基础设施太累了**。

你需要：
- 让 Agent 先计划再行动（不是瞎搞）
- 出错时自动分类和处理（不是死循环重试）
- 控制工具暴露数量（不是一把梭）
- 监控运行指标（不是黑盒）
- 权限管理（不是谁都能删文件）
- 对外通信协议（不是自嗨）

AutoAgentKit 把这 6 个能力打包成一个 pip 包，开箱即用。

## 安装

```bash
pip install auto-agent-kit
```

依赖：Python 3.8+，零外部依赖。

## 6 大模块实战

### 1. PlanMode — 让 Agent 先计划再行动

```python
from auto_agent_kit import PlanMode

planner = PlanMode()

# 创建一个多步骤计划
plan = planner.create_plan(
    objective="分析竞品并生成报告",
    steps=[
        {"id": "1", "description": "搜索竞品信息", "depends_on": []},
        {"id": "2", "description": "提取关键功能对比", "depends_on": ["1"]},
        {"id": "3", "description": "生成分析报告", "depends_on": ["2"]},
    ]
)

# 执行下一步
next_step = planner.get_next_step(plan)
# 执行完成后标记
planner.complete_step(plan, "1")
```

**适用场景：** 数据分析、报告生成、多步骤工作流

### 2. ErrorReflection — 错误自动分类 + 智能恢复

```python
from auto_agent_kit import ErrorReflection

reflection = ErrorReflection()

# 自动分类错误
result = reflection.reflect(
    error_type="RateLimitError",
    context={"retry_after": 30, "provider": "openai"}
)
# result.category -> "rate_limit"
# result.recovery -> "wait_and_retry"

# 获取恢复策略
strategy = reflection.get_recovery("rate_limit")
# strategy -> {"action": "exponential_backoff", "max_retries": 3}
```

**支持 20+ 错误类型：** auth / billing / rate_limit / timeout / context_overflow / validation / network / parse / permission 等

### 3. ToolRouter — 阶段性工具暴露，不一把梭

```python
from auto_agent_kit import ToolRouter

router = ToolRouter()

# 定义阶段
router.register_phase("research", max_tools=3)
router.register_phase("analysis", max_tools=4)
router.register_phase("output", max_tools=2)

# 注册工具到阶段
router.register_tool("web_search", phase="research")
router.register_tool("web_fetch", phase="research")
router.register_tool("data_analyze", phase="analysis")

# 获取当前阶段可用工具
tools = router.get_available_tools("research")
# -> ["web_search", "web_fetch"]
```

**核心原则：** 每个阶段暴露 ≤ 8 个工具，避免上下文污染

### 4. Dashboard — 实时监控指标

```python
from auto_agent_kit import Dashboard

dashboard = Dashboard()

# 记录事件
dashboard.record_event("task_start", {"task": "竞品分析"})
dashboard.record_event("tool_call", {"tool": "web_search", "duration_ms": 1200})
dashboard.record_event("error", {"type": "rate_limit", "retry_count": 1})

# 获取统计
stats = dashboard.get_stats()
# stats.tool_success_rate -> 0.95
# stats.avg_duration_ms -> 850
# stats.error_count -> 3
```

### 5. AccessControl — 4 级权限管理

```python
from auto_agent_kit import AccessControl

ac = AccessControl()

# 定义权限级别
ac.define_level("read", ["read_file", "search"])
ac.define_level("write", ["read_file", "search", "write_file"])
ac.define_level("admin", ["read_file", "search", "write_file", "exec"])
ac.define_level("safe", ["read_file"])  # 只读沙箱

# 检查权限
ac.check_permission("read_file", "read")   # True
ac.check_permission("exec", "read")        # False
```

### 6. MCPServer — JSON-RPC 2.0 + SSE 协议服务器

```python
from auto_agent_kit import MCPServer

server = MCPServer(host="0.0.0.0", port=8901)

# 注册工具
server.register_tool(
    name="search",
    handler=lambda params: {"results": ["result1", "result2"]},
    description="搜索工具"
)

# 启动服务器（异步）
# await server.start()
```

## 完整示例：搭建一个调研 Agent

```python
from auto_agent_kit import PlanMode, ErrorReflection, ToolRouter, Dashboard

planner = PlanMode()
router = ToolRouter()
dashboard = Dashboard()
reflection = ErrorReflection()

# 1. 规划
plan = planner.create_plan("调研AI Agent框架", [
    {"id": "1", "description": "搜索主流框架", "depends_on": []},
    {"id": "2", "description": "对比功能特性", "depends_on": ["1"]},
    {"id": "3", "description": "输出推荐方案", "depends_on": ["2"]},
])

# 2. 阶段控制
router.register_phase("research", max_tools=3)
router.register_phase("analysis", max_tools=4)
router.register_phase("output", max_tools=2)

# 3. 执行 + 监控
for step in plan["steps"]:
    try:
        dashboard.record_event("step_start", step)
        # 执行步骤...
        dashboard.record_event("step_complete", step)
    except Exception as e:
        recovery = reflection.get_recovery(type(e).__name__)
        dashboard.record_event("error", {"step": step["id"], "error": str(e)})

# 4. 查看报告
print(dashboard.get_report())
```

## 进阶用法

### 组合 PlanMode + ErrorReflection

```python
# 自动重试失败步骤
step_result = planner.execute_with_retry(
    step=step,
    max_retries=3,
    on_error=lambda e: reflection.get_recovery(type(e).__name__)
)
```

### 组合 ToolRouter + Dashboard

```python
# 监控工具使用频率
for phase in ["research", "analysis", "output"]:
    tools = router.get_available_tools(phase)
    for tool in tools:
        dashboard.track_tool_usage(tool, phase)
```

## 项目结构

```
auto_agent_kit/
├── __init__.py          # 统一导出
├── core/
│   ├── plan_mode.py     # 计划执行模式
│   ├── error_reflection.py  # 错误反射
│   ├── tool_router.py   # 工具路由器
│   ├── dashboard.py     # 仪表板
│   ├── access_control.py    # 访问控制
│   └── mcp_server.py    # MCP 协议服务器
├── examples/
│   └── demo.py          # 完整示例
└── tests/
    └── test_all.py      # 单元测试
```

## 下一步

- ⭐ GitHub 点星：`https://github.com/Lwh909193/auto-agent-kit`
- 📦 PyPI 安装：`pip install auto-agent-kit`
- 📖 中文 README：`README_CN.md`
- 🚀 v0.2.0 规划：异步支持、更多错误类型、插件系统

## 贡献

欢迎 PR、Issue、Star！一起把 AutoAgentKit 做成 AI Agent 开发者的标配工具包。
