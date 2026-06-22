# Building Production-Grade AI Agents with AutoAgentKit

**A practical Python toolkit born from real-world agent engineering — not another framework, but a collection of battle-tested patterns.**

---

## The Problem

Every AI agent starts the same way: a simple loop — think, act, observe. It works for demos. But when you need an agent that runs reliably in production, you quickly discover that the hard problems aren't about calling an LLM. They're about:

- **Planning**: How do you decompose a complex task into executable steps?
- **Error handling**: What happens when an API call fails for the 5th time?
- **Tool management**: How do you prevent the agent from using 20 tools at once?
- **Observability**: How do you know what your agent is actually doing?
- **Safety**: How do you control what operations the agent can perform?
- **Context**: How do you keep the agent focused when the conversation gets long?

These are the problems **AutoAgentKit** was built to solve.

---

## What is AutoAgentKit?

AutoAgentKit is a **Python toolkit for building production-grade AI agents**. It's not a framework that dictates how you should build your agent — it's a collection of modular, independently usable components that solve specific real-world problems.

Current version: **v0.3.0** (8 core modules)

### The 8 Core Modules

#### 1. PlanMode — Plan-Execute Separation
```python
from auto_agent_kit import PlanMode

planner = PlanMode()
plan = planner.create_plan("Build a REST API with FastAPI")
# Plan: 1. Setup project → 2. Define models → 3. Create routes → 4. Add tests
executor = planner.execute(plan)
```

Separates *what to do* from *how to do it*. The planner thinks, the executor acts. This prevents the agent from changing its plan mid-execution.

#### 2. AsyncPlanMode — Concurrent Step Execution
```python
from auto_agent_kit import AsyncPlanMode

async_planner = AsyncPlanMode()
results = await async_planner.run_plan([
    ("Scrape site A", scrape_a),
    ("Scrape site B", scrape_b),  # Runs in parallel
    ("Merge results", merge),     # Waits for both
])
```

For workflows where independent steps can run concurrently. Includes timeout control per step.

#### 3. ErrorReflection — Intelligent Error Recovery
```python
from auto_agent_kit import ErrorReflection

reflection = ErrorReflection()
error_type = reflection.classify("HTTP 429 Too Many Requests")
# → ErrorCategory.RATE_LIMIT
strategy = reflection.get_strategy(error_type)
# → RecoveryStrategy.BACKOFF (retry with exponential backoff)
```

Classifies errors into 20+ categories (auth, rate_limit, timeout, context_overflow, etc.) and applies the right recovery strategy automatically.

#### 4. ToolRouter — Phase-Based Tool Exposure
```python
from auto_agent_kit import ToolRouter

router = ToolRouter()
router.add_phase("research", [search_tool, fetch_tool])
router.add_phase("implement", [write_tool, test_tool])
router.activate("research")
# Only 2 tools visible — prevents tool overload
```

Controls which tools are available at each stage of work. Never more than 8 tools per phase. Prevents the "tool overload" problem where agents get confused by too many options.

#### 5. Dashboard — Real-Time Metrics
```python
from auto_agent_kit import Dashboard

dashboard = Dashboard()
dashboard.record("tool_call", duration_ms=245, success=True)
dashboard.record("error", category="rate_limit")
report = dashboard.summary()
# → {"total_calls": 142, "avg_duration": 189ms, "error_rate": 2.1%}
```

Built-in metrics collection with no external dependencies. Track tool calls, errors, durations, and success rates.

#### 6. AccessControl — 4-Level Permission System
```python
from auto_agent_kit import AccessControl

acl = AccessControl()
acl.grant("reader", ["read", "search"])
acl.grant("operator", ["read", "search", "write", "execute"])

acl.check("reader", "delete")  # → False (denied)
acl.check("operator", "delete")  # → False (requires admin)
```

Four permission levels: reader, operator, admin, superadmin. Every tool call can be checked against the policy before execution.

#### 7. ContextCompressor — Incremental Context Compression *(New in v0.3.0)*
```python
from auto_agent_kit import ContextCompressor

compressor = ContextCompressor(max_tokens=4000)
compressed = compressor.compress(
    long_conversation,
    key_instructions="Remember: user prefers Python"
)
# Structured: [goal], [progress], [error], [instructions]
```

Structured segment-based compression with instruction re-injection. Prevents context overflow without losing critical information.

#### 8. TaskLock — Distributed Task Locking *(New in v0.3.0)*
```python
from auto_agent_kit import TaskLock

lock = TaskLock()
with lock("data-pipeline", timeout=300):
    # Critical section — no other process can enter
    process_data()
```

File-based distributed locking with auto-expiry. Prevents concurrent execution of the same task across processes. 5-minute default timeout prevents deadlocks.

---

## Why Not LangChain / CrewAI / Agno?

| Feature | AutoAgentKit | LangChain | CrewAI |
|---------|-------------|-----------|--------|
| Lines of code to start | ~5 | ~30 | ~50 |
| Plan-Execute separation | ✅ Built-in | ❌ Custom | ❌ Custom |
| Error classification | ✅ 20+ types | ❌ Basic | ❌ Basic |
| Tool phase control | ✅ Built-in | ❌ Custom | ❌ Custom |
| Access control | ✅ 4 levels | ❌ None | ❌ None |
| Context compression | ✅ Structured | ❌ None | ❌ None |
| Task locking | ✅ Distributed | ❌ None | ❌ None |
| Dependencies | Minimal | Heavy | Heavy |
| Learning curve | Low | Medium | High |

AutoAgentKit is **not** trying to be a full-stack agent framework. It's a toolkit for developers who already know how to build agents but need battle-tested solutions to specific production problems.

---

## Real-World Usage

AutoAgentKit was extracted from a production agent system with:
- 102 skills across 8 architecture layers
- 17 knowledge bases (1,342 files)
- 6 integrated subsystems
- Daily cron-driven autonomous operation

Every module in AutoAgentKit was first built to solve a real problem, then extracted, tested, and documented. This is not ivory-tower architecture — it's engineering that has been debugged in production.

---

## Getting Started

```bash
pip install auto-agent-kit
```

```python
from auto_agent_kit import PlanMode, ErrorReflection, ToolRouter

# Plan your task
planner = PlanMode()
plan = planner.create_plan("Research and summarize AI trends")

# Route tools by phase
router = ToolRouter()
router.add_phase("research", [search, fetch])
router.add_phase("analyze", [summarize, compare])
router.activate("research")

# Handle errors gracefully
reflection = ErrorReflection()
```

Full tutorial: [TUTORIAL_CN.md](https://github.com/Lwh909193/auto-agent-kit/blob/main/TUTORIAL_CN.md)

---

## What's Next

- **v0.4.0**: Memory system integration (Mem0/Memanto adapters)
- **v0.5.0**: Multi-agent orchestration
- **v0.6.0**: Built-in evaluation harness

---

## The Philosophy

**Production agents are not about the LLM. They're about the infrastructure around it.**

A good agent framework doesn't make the LLM smarter. It makes the LLM more reliable, more observable, and more controllable. That's what AutoAgentKit does.

---

*AutoAgentKit is open source under MIT. Contributions welcome at [github.com/Lwh909193/auto-agent-kit](https://github.com/Lwh909193/auto-agent-kit).*
