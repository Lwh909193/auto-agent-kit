"""AutoAgentKit 测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auto_agent_kit import (
    PlanMode, ErrorReflection, ErrorCategory, RecoveryStrategy,
    ToolRouter, ToolPhase, Dashboard, AccessControl, PermissionLevel,
    MCPServer,
    Plugin, PluginManager, LoggingPlugin, MetricsPlugin,
    AsyncPlanMode, AsyncStepResult, run_plan,
)


import asyncio


def test_plan_mode():
    p = PlanMode()
    plan = p.create_plan("test", ["step1", "step2"])
    assert len(plan.steps) == 2
    assert plan.progress == 0.0

    p.start_step("step_1")
    p.complete_step("step_1", "done")
    assert plan.progress == 0.5

    next_step = plan.get_next_ready()
    assert next_step is not None
    assert next_step.id == "step_2"

    status = p.get_plan_status()
    assert status["goal"] == "test"
    assert status["progress"] == 0.5
    print("  ✅ PlanMode")


def test_error_reflection():
    r = ErrorReflection()

    # 分类测试
    assert r.classify("rate limit exceeded") == ErrorCategory.RATE_LIMIT
    assert r.classify("timeout after 30s") == ErrorCategory.TIMEOUT
    assert r.classify("invalid api key") == ErrorCategory.AUTH_INVALID
    assert r.classify("context length exceeded") == ErrorCategory.CONTEXT_OVERFLOW
    assert r.classify("random unknown error") == ErrorCategory.UNKNOWN

    # 恢复策略测试
    result = r.classify_and_recover(Exception("rate limit"), "test")
    assert result["strategy"] == RecoveryStrategy.EXPONENTIAL_BACKOFF.value

    result = r.classify_and_recover(Exception("auth failed"), "test")
    assert result["strategy"] == RecoveryStrategy.ROTATE_CREDENTIAL.value

    # 连续失败升级
    for _ in range(3):
        r.classify_and_recover(Exception("timeout"), "api")
    last = r.classify_and_recover(Exception("timeout"), "api")
    assert last["upgraded"] is True

    stats = r.get_stats()
    assert stats["total"] > 0
    print("  ✅ ErrorReflection")


def test_tool_router():
    r = ToolRouter()
    r.register("search", "搜索", ToolPhase.INIT)
    r.register("execute", "执行", ToolPhase.EXECUTE)

    active = r.get_active_tools()
    assert len(active) == 1
    assert active[0].name == "search"

    r.set_phase(ToolPhase.EXECUTE)
    active = r.get_active_tools()
    assert len(active) == 1
    assert active[0].name == "execute"

    r.use_tool("execute")
    stats = r.get_stats()
    assert stats["usage"]["execute"]["count"] == 1
    print("  ✅ ToolRouter")


def test_dashboard():
    d = Dashboard()
    d.record("cpu", 50)
    d.record("cpu", 60)
    d.record_tool_call("search", True, 100)

    cpu = d.get_metric("cpu")
    assert cpu is not None
    assert cpu.last == 60
    assert cpu.avg == 55

    snapshot = d.get_snapshot()
    assert "uptime_seconds" in snapshot
    assert snapshot["metrics"]["cpu"]["count"] == 2
    print("  ✅ Dashboard")


def test_access_control():
    ac = AccessControl()
    ac.add_default_rules()

    # SAFE 操作自动允许
    result = ac.check("read:workspace/data.csv")
    assert result["granted"] is True

    # DANGEROUS 操作需要审批
    result = ac.check("delete:workspace/data.csv")
    assert result["granted"] is False
    assert result["needs_approval"] is True

    # 审批流程
    approval = ac.request_approval("delete:data.csv", "清理旧数据")
    assert ac.approve(approval["id"]) is True

    stats = ac.get_stats()
    assert stats["total_checks"] >= 2
    print("  ✅ AccessControl")


def test_mcp_server():
    s = MCPServer(port=8901)

    def test_handler(query: str = "") -> str:
        return f"result: {query}"

    s.register_tool("test_tool", "测试工具", test_handler)

    # list_tools
    resp = s.handle_request({"jsonrpc": "2.0", "method": "list_tools", "id": "1"})
    assert "result" in resp
    assert len(resp["result"]["tools"]) == 1

    # ping
    resp = s.handle_request({"jsonrpc": "2.0", "method": "ping", "id": "2"})
    assert resp["result"]["pong"] is True

    # call_tool
    resp = s.handle_request({
        "jsonrpc": "2.0", "method": "call_tool", "id": "3",
        "params": {"name": "test_tool", "arguments": {"query": "hello"}},
    })
    assert "result" in resp
    assert "hello" in resp["result"]["content"][0]["text"]

    # unknown method
    resp = s.handle_request({"jsonrpc": "2.0", "method": "unknown", "id": "4"})
    assert "error" in resp

    stats = s.get_stats()
    assert stats["tools_registered"] == 1
    print("  ✅ MCPServer")


def test_plugin_system():
    pm = PluginManager()

    # 注册插件
    log_plugin = LoggingPlugin()
    assert pm.register(log_plugin) is True
    assert pm.register(log_plugin) is False  # 重复注册
    assert pm.is_registered("logging") is True

    # 插件列表
    plugins = pm.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "logging"

    # 钩子系统
    def custom_hook(step: dict):
        step["modified"] = True
        return step

    pm.add_hook("before_step", custom_hook, "test", priority=10)
    assert pm.has_hooks("before_step") is True

    # 触发钩子
    result = pm.on_before_step({"id": "1", "description": "test"})
    assert result["modified"] is True

    # 错误钩子
    pm.on_error(Exception("test error"), {"step": "1"})

    # 移除钩子
    assert pm.remove_hook("before_step", custom_hook) is True

    # 统计
    stats = pm.get_stats()
    assert stats["total_plugins"] == 1
    assert stats["total_hooks"] >= 0

    # 注销
    assert pm.unregister("logging") is True
    assert pm.is_registered("logging") is False
    print("  ✅ PluginSystem")


def test_metrics_plugin():
    mp = MetricsPlugin()
    mp.on_after_step({"id": "1", "duration": 0.1}, "ok")
    mp.on_after_step({"id": "2", "duration": 0.2}, "ok")
    mp.on_error(Exception("fail"), {})

    report = mp.get_report()
    assert report["total_steps"] == 2
    assert report["total_errors"] == 1
    assert report["error_rate"] == 0.5
    assert abs(report["avg_duration_ms"] - 150.0) < 0.001
    print("  ✅ MetricsPlugin")


def test_async_plan():
    async def run():
        ap = AsyncPlanMode(max_retries=1, concurrency_limit=2)

        def executor(desc: str) -> str:
            return f"done: {desc}"

        results = await run_plan(ap, ["step1", "step2", "step3"], executor)
        assert len(results) == 3
        assert all(r.status == "ok" for r in results)
        assert results[0].result == "done: step1"

        # 并发执行
        ap2 = AsyncPlanMode()
        plan = ap2.create_plan("concurrent", ["a", "b", "c"])
        concurrent_results = await ap2.execute_concurrently_async(executor, plan)
        assert len(concurrent_results) == 3
        assert all(r.status == "ok" for r in concurrent_results)

        # 超时测试
        async def slow_executor(desc: str) -> str:
            await asyncio.sleep(10)
            return "slow"

        timeout_result = await ap2.execute_with_timeout(slow_executor, "slow", 0.1)
        assert timeout_result.status == "timeout"

        return True

    assert asyncio.run(run()) is True
    print("  ✅ AsyncPlan")


if __name__ == "__main__":
    print("AutoAgentKit 测试\n")
    test_plan_mode()
    test_error_reflection()
    test_tool_router()
    test_dashboard()
    test_access_control()
    test_mcp_server()
    test_plugin_system()
    test_metrics_plugin()
    test_async_plan()
    print("\n全部测试通过 ✅")
