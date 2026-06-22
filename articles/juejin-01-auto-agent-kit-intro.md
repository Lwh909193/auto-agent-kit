# 🦞 AutoAgentKit：从实战中提炼的生产级 AI Agent 工具包

> 当 LangChain 太重、CrewAI 太玩具、AutoGen 太学术——你需要一个真正能上生产的 Agent 框架。

## 为什么还要一个新的 Agent 框架？

市面上 Agent 框架很多，但我在实际项目中反复遇到同样的问题：

| 问题 | 你的框架怎么处理？ |
|------|------------------|
| 工具调用失败后盲目重试 | ❌ 大部分框架只会 `try/except` |
| 上下文膨胀导致 Agent 质量下降 | ❌ 没有人管 |
| 工具太多模型选错 | ❌ 所有工具堆在一起 |
| 不知道 Agent 在干什么 | ❌ 黑盒运行 |
| 权限失控 | ❌ 没有权限体系 |
| 协议不标准 | ❌ 自研协议，无法互通 |

**AutoAgentKit 的目标很简单：** 把我在真实系统中验证过的 6 个生产级能力打包成一个 pip install 就能用的工具包。

## 快速上手

```bash
pip install auto-agent-kit
```

```python
from auto_agent_kit import PlanMode, ErrorReflection, ToolRouter

# === 1. 计划执行模式 ===
planner = PlanMode()
plan = planner.create_plan("分析市场数据并生成报告")
# 自动解析步骤依赖：收集数据 → 分析趋势 → 生成报告

# === 2. 错误反射 ===
reflector = ErrorReflection()
recovery = reflector.classify_and_recover(error)
# 自动分类错误类型，精确恢复策略

# === 3. 工具路由器 ===
router = ToolRouter()
router.register_phase("research", ["web_search", "web_fetch"])
router.register_phase("analyze", ["code_executor", "data_visualizer"])
router.activate_phase("research")
# 每阶段只暴露 ≤8 个工具，减少模型选择负担
```

## 6 大核心模块详解

### 1. PlanMode — 计划执行模式

不是让 Agent 边想边做，而是**先计划，再执行**。

```python
planner = PlanMode()
plan = planner.create_plan("调研竞品并生成报告", [
    "搜索竞品信息",
    "抓取竞品官网详情",
    "对比分析功能差异",
    "生成调研报告"
])

planner.start_step("step_1")
# 执行搜索...
planner.complete_step("step_1", "搜索完成，找到 10 个竞品")

next_step = plan.get_next_ready()  # 自动解析依赖，返回可执行的下一步
```

**为什么需要 PlanMode？** 因为 Agent 在长任务中容易「跑偏」。先定计划再执行，每一步都清楚自己在做什么。

### 2. ErrorReflection — 错误反射

工具调用失败是常态。关键是**怎么恢复**。

```python
reflector = ErrorReflection()

# 自动分类 + 精确恢复策略
result = reflector.classify_and_recover(error, context="api_call")
# → {"category": "rate_limit", "strategy": "exponential_backoff", "retry_after": 5}

# 连续失败自动升级
for _ in range(3):
    reflector.classify_and_recover(error, "api")
# 第 4 次 → {"upgraded": true, "strategy": "fallback_provider"}
```

支持 20+ 错误类型：限流、超时、认证失效、上下文溢出、服务不可用……每种都有精确恢复策略。

### 3. ToolRouter — 工具路由器

**不要一次性给 Agent 50 个工具。** 阶段性暴露，每阶段 ≤8 个。

```python
router = ToolRouter()
router.register("web_search", "网页搜索", ToolPhase.INIT)
router.register("code_executor", "代码执行", ToolPhase.EXECUTE)

router.set_phase(ToolPhase.INIT)
# 当前只暴露搜索工具

router.set_phase(ToolPhase.EXECUTE)
# 切换到执行阶段，暴露代码执行工具
```

### 4. Dashboard — 仪表板

实时监控 Agent 的每一个动作。

```python
dashboard = Dashboard()
dashboard.record("cpu", 50)
dashboard.record_tool_call("web_search", success=True, duration_ms=1200)

snapshot = dashboard.get_snapshot()
# → {"metrics": {"cpu": {"last": 50, "avg": 45, "count": 2}}, ...}
```

### 5. AccessControl — 访问控制

4 级权限策略：SAFE → SENSITIVE → DANGEROUS → CRITICAL。

```python
ac = AccessControl()
ac.add_default_rules()

# 安全操作自动允许
result = ac.check("read:workspace/data.csv")
# → {"granted": true}

# 危险操作需要审批
result = ac.check("delete:workspace/data.csv")
# → {"granted": false, "needs_approval": true}

# 审批流程
approval = ac.request_approval("delete:data.csv", "清理旧数据")
ac.approve(approval["id"])
```

### 6. MCPServer — MCP 协议服务器

标准 JSON-RPC 2.0 + SSE，让任何 MCP 客户端都能调用你的工具。

```python
server = MCPServer(port=8901)

@server.register_tool("search", "搜索工具")
def search(query: str = "") -> str:
    return f"搜索结果: {query}"

server.start()  # SSE 服务端启动
```

## v0.2.0 新特性

最新版本新增了 **插件系统** 和 **异步支持**：

### 插件系统

```python
from auto_agent_kit import PluginManager, LoggingPlugin, MetricsPlugin

pm = PluginManager()
pm.register(LoggingPlugin())
pm.register(MetricsPlugin())

# 钩子系统
pm.add_hook("before_step", my_custom_hook, priority=10)
pm.on_before_step({"id": "1", "description": "执行搜索"})
```

### 异步计划执行

```python
from auto_agent_kit import AsyncPlanMode, run_plan

async def main():
    ap = AsyncPlanMode(concurrency_limit=2)
    results = await run_plan(ap, ["step1", "step2", "step3"], executor)
    # 并发执行，自动超时控制
```

## 为什么你应该试试？

1. **轻量** — 零依赖核心，pip install 即用
2. **生产验证** — 每个模块都来自真实系统
3. **标准协议** — MCP 协议，与其他工具互通
4. **渐进式** — 可以只用 1 个模块，也可以全部用
5. **中文友好** — 文档和注释都有中文版

## 快速开始

```bash
pip install auto-agent-kit
```

完整文档和示例：
- GitHub: https://github.com/Lwh909193/auto-agent-kit
- PyPI: https://pypi.org/project/auto-agent-kit/
- 中文教程: https://github.com/Lwh909193/auto-agent-kit/blob/master/TUTORIAL_CN.md

---

**AutoAgentKit 还在早期阶段，欢迎 Star、Issue、PR！**

如果你在项目中用了，或者有什么想法，欢迎在评论区交流。你的反馈会直接影响下一个版本的方向。

🦞 让我们一起把 AI Agent 从玩具变成生产力工具。
