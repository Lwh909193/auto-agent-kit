# AutoAgentKit 🦞

> **生产级 AI Agent 工具包** — 从实战中提炼，已在真实系统中验证。
>
> 6 大核心模块：PlanMode（计划执行模式） · ErrorReflection（错误反射） · ToolRouter（工具路由器） · Dashboard（仪表板） · AccessControl（访问控制） · MCPServer（MCP协议服务器）

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI/CD](https://github.com/Lwh909193/auto-agent-kit/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Lwh909193/auto-agent-kit/actions)
[![PyPI](https://img.shields.io/badge/pypi-v0.1.0-orange)](https://pypi.org/project/auto-agent-kit/)

---

## 为什么用 AutoAgentKit？

市面上 Agent 框架很多（LangChain、CrewAI、AutoGen），但它们普遍缺少**生产级工程能力**：

| 问题 | AutoAgentKit 方案 |
|------|------------------|
| 工具调用失败后盲目重试 | **ErrorReflection** — 20+ 错误类型自动分类，精确恢复策略 |
| 上下文膨胀导致质量下降 | **PlanMode** — Plan/Act 分离，步骤依赖解析 |
| 工具太多模型选错 | **ToolRouter** — 阶段性暴露，每阶段 ≤ 8 工具 |
| 不知道 Agent 在干什么 | **Dashboard** — 实时指标监控 |
| 权限失控 | **AccessControl** — 4 级权限策略 |
| 协议不标准 | **MCPServer** — JSON-RPC 2.0 + SSE |

## 快速开始

```bash
pip install auto-agent-kit
```

```python
from auto_agent_kit import PlanMode, ErrorReflection, ToolRouter

# === 计划执行模式 ===
planner = PlanMode()
plan = planner.create_plan("分析市场数据并生成报告")
# → ["收集数据", "分析趋势", "生成报告"]

# === 错误反射 ===
reflector = ErrorReflection()
recovery = reflector.classify_and_recover(error)
# → {"type": "rate_limit", "strategy": "exponential_backoff", "retry_after": 5}

# === 工具路由器 ===
router = ToolRouter()
router.register_phase("research", ["web_search", "web_fetch"])
router.register_phase("analyze", ["code_executor", "data_visualizer"])
router.activate_phase("research")
# → 当前只暴露 research 阶段的工具
```

## 安装

```bash
# 基础安装（核心模块）
pip install auto-agent-kit

# 带 MCP Server 支持
pip install auto-agent-kit[mcp]

# 带 Dashboard 支持
pip install auto-agent-kit[dashboard]

# 全部功能
pip install auto-agent-kit[all]
```

## 模块详解

### 🎯 PlanMode — 计划执行模式

复杂任务先计划再行动。支持：

- Plan/Act 分离 — 计划阶段和执行阶段独立
- 步骤依赖解析 — 自动识别步骤间依赖关系
- 进度追踪 — 实时了解执行到哪一步

```python
from auto_agent_kit import PlanMode

planner = PlanMode()
plan = planner.create_plan("调研竞品并输出对比报告")
# 输出：["搜索竞品信息", "抓取详情页", "分析差异", "生成报告"]
```

### 🔧 ErrorReflection — 错误反射

工具调用失败时自动分类，精确恢复。支持 **20+ 错误类型**：

| 错误类型 | 恢复策略 | 说明 |
|---------|---------|------|
| `rate_limit` | 指数退避 | API 限流，等待后重试 |
| `timeout` | 超时重试 | 连接超时，增加超时时间 |
| `auth_failed` | 凭证轮换 | 认证失败，切换凭证 |
| `context_overflow` | 上下文压缩 | 上下文超限，压缩后重试 |
| `service_unavailable` | 服务切换 | 服务不可用，切备用 |
| `parse_error` | 格式修复 | 解析失败，修复格式 |

```python
from auto_agent_kit import ErrorReflection

reflector = ErrorReflection()
result = reflector.classify_and_recover({
    "error": "429 Too Many Requests",
    "status_code": 429
})
# → {"type": "rate_limit", "strategy": "exponential_backoff", "retry_after": 5}
```

### 🧭 ToolRouter — 语义工具路由器

阶段性工具暴露，防止模型被过多工具干扰。

```python
from auto_agent_kit import ToolRouter

router = ToolRouter()
router.register_phase("research", ["web_search", "web_fetch", "news_api"])
router.register_phase("analyze", ["code_executor", "data_visualizer"])
router.register_phase("report", ["doc_generator", "pdf_exporter"])

router.activate_phase("research")
available = router.get_available_tools()
# → ["web_search", "web_fetch", "news_api"]  (≤ 8 工具)
```

### 📊 Dashboard — 仪表板

实时监控 Agent 运行指标。

```python
from auto_agent_kit import Dashboard

dashboard = Dashboard()
dashboard.record_event("tool_call", {"tool": "web_search", "status": "success"})
dashboard.record_event("error", {"type": "rate_limit", "recovery": "backoff"})

stats = dashboard.get_stats()
# → {"total_calls": 42, "success_rate": 0.95, "error_rate": 0.05}
```

### 🔒 AccessControl — 访问控制

4 级权限策略 + 操作审批流程。

| 级别 | 说明 | 示例操作 |
|------|------|---------|
| L1 Read | 只读 | 文件读取、搜索 |
| L2 Execute | 执行 | 运行脚本、API 调用 |
| L3 Modify | 修改 | 文件写入、配置变更 |
| L4 Admin | 管理 | 删除、格式化、系统配置 |

```python
from auto_agent_kit import AccessControl

ac = AccessControl()
ac.check_permission("delete_file", level="L3")
# → {"allowed": False, "reason": "需要 L4 权限", "requires_approval": True}
```

### 🌐 MCPServer — MCP 协议服务器

JSON-RPC 2.0 + SSE 传输，兼容任何 MCP 客户端。

```python
from auto_agent_kit import MCPServer

server = MCPServer(port=8901)
server.register_tool("search", search_handler)
server.register_tool("analyze", analyze_handler)
server.start()  # 启动 SSE 服务器
```

## 完整示例

```python
from auto_agent_kit import PlanMode, ErrorReflection, ToolRouter, Dashboard, AccessControl

# 1. 创建计划
planner = PlanMode()
plan = planner.create_plan("调研 AI Agent 市场趋势")

# 2. 配置工具
router = ToolRouter()
router.register_phase("research", ["web_search", "web_fetch"])

# 3. 监控
dashboard = Dashboard()

# 4. 执行（带错误处理）
reflector = ErrorReflection()
for step in plan:
    try:
        router.activate_phase("research")
        result = execute_step(step, router.get_available_tools())
        dashboard.record_event("step_complete", {"step": step})
    except Exception as e:
        recovery = reflector.classify_and_recover(e)
        dashboard.record_event("error", {"step": step, "recovery": recovery})
```

## 开发

```bash
git clone git@github.com:Lwh909193/auto-agent-kit.git
cd auto-agent-kit
pip install -e ".[all]"
pytest tests/ -v
```

## 发布

```bash
python scripts/publish.py
```

## 路线图

- [x] v0.1.0 — 6 大核心模块 + 测试
- [ ] v0.2.0 — 异步支持 + 更多错误类型
- [ ] v0.3.0 — 插件系统 + 第三方集成
- [ ] v1.0.0 — 生产就绪 + 完整文档

## 许可证

MIT © 2026 AoLongZhiZun（鳌龙至尊）
