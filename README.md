# AutoAgentKit

> 一个实用的 Python 工具包，用于构建生产级 AI Agent（人工智能代理）。
> 从实战中提炼，已在真实系统中验证。

## 特性

| 模块 | 说明 |
|------|------|
| **PlanMode** | 计划执行模式 — 复杂任务先计划再行动，支持 Plan/Act 分离 |
| **ErrorReflection** | 错误反射 — 工具失败自动分类（20+类型），精确恢复策略 |
| **ToolRouter** | 语义工具路由器 — 阶段性工具暴露，每阶段 ≤ 8 工具 |
| **Dashboard** | 仪表板 — 实时监控 Agent 运行指标 |
| **AccessControl** | 访问控制 — 4 级权限策略 + 操作审批 |
| **MCPServer** | MCP 协议服务器 — JSON-RPC 2.0 + SSE 传输 |

## 快速开始

```bash
pip install auto-agent-kit
```

```python
from auto_agent_kit import PlanMode, ErrorReflection

# 计划执行模式
planner = PlanMode()
plan = planner.create_plan("分析市场数据并生成报告")
# → ["收集数据", "分析趋势", "生成报告"]

# 错误反射
reflector = ErrorReflection()
recovery = reflector.classify_and_recover(error)
# → {"type": "rate_limit", "strategy": "exponential_backoff"}
```

## 安装

```bash
pip install auto-agent-kit
# 或带全部依赖
pip install auto-agent-kit[all]
```

## 文档

详见 [docs/](docs/) 目录。

## 许可证

MIT
