# Changelog

## v0.4.0 (2026-06-26)

### 🚀 新增模块

#### 🔀 StateGraph — 图编排引擎
- LangGraph 灵感纯 Python 实现，零外部依赖
- 3 种边类型：NORMAL / CONDITIONAL / LOOP
- 6 种节点类型：TASK / DECISION / PARALLEL / INPUT / OUTPUT / SUBGRAPH
- 3 个便捷构建器：sequential() / agent_loop() / branching()
- 检查点系统：自动保存/恢复执行状态
- Mermaid 可视化：自动生成流程图
- 错误容忍：失败节点自动跳过
- 46/46 测试通过

#### 👥 CrewRole — 角色协作系统
- CrewAI 灵感角色定义框架
- Role：角色定义（名称/目标/工具/系统提示）
- Task：任务定义（描述/角色/期望输出/上下文）
- Crew：团队编排（顺序/层级/并行/自定义流程）
- 便捷工厂：create_analysis_team() / create_development_team()
- 87/87 测试通过

#### 🏷️ TypedAgent — 类型安全 Agent
- Pydantic AI 灵感类型安全工具定义
- TypedTool：装饰器定义类型安全工具，自动参数校验与转换
- TypedAgent：FastAPI 风格 Agent 定义
- StructuredOutput：dataclass 驱动结构化输出
- 支持 str/int/float/bool/list/dict/Optional/Literal/Enum/dataclass
- 88/88 测试通过

### 🔧 增强

#### MCP Server — Resources/Prompts 原语
- 新增 MCPResource / MCPResourceTemplate / MCPPrompt 等 dataclass
- 新增 register_resource() / register_prompt() 等方法
- 新增 list_resources / read_resource / list_prompts / get_prompt JSON-RPC 方法
- 41/41 测试通过

### 📦 其他
- 测试覆盖率：262 项测试全部通过
- 新增 ~99KB 代码
- 更新 README 文档
