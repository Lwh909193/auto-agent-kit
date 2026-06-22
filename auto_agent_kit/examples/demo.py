"""AutoAgentKit 使用示例"""

from auto_agent_kit import (
    PlanMode, ErrorReflection, ToolRouter, ToolPhase,
    Dashboard, AccessControl, MCPServer,
)


def example_plan_mode():
    """PlanMode 示例"""
    planner = PlanMode(max_retries=2)

    # 创建计划
    plan = planner.create_plan(
        goal="分析市场数据并生成报告",
        steps=[
            "收集市场数据",
            "分析趋势",
            "生成报告",
        ],
    )

    # 模拟执行
    def executor(step: str) -> str:
        print(f"  执行: {step}")
        return f"{step} 完成"

    results = planner.execute_sequentially(executor)
    print(f"  状态: {planner.get_plan_status()['summary']}")
    return results


def example_error_reflection():
    """ErrorReflection 示例"""
    reflector = ErrorReflection(max_retries=3)

    # 模拟各种错误
    errors = [
        ("rate limit exceeded, retry after 60s", "openai"),
        ("Connection refused: api.example.com:443", "http"),
        ("context length exceeded, max 8192 tokens", "llm"),
        ("invalid api key provided", "auth"),
        ("[Errno 11001] getaddrinfo failed", "dns"),
    ]

    for msg, source in errors:
        result = reflector.classify_and_recover(Exception(msg), source)
        print(f"  [{source}] {result['category']:20s} → {result['strategy']:25s}")

    stats = reflector.get_stats()
    print(f"  总计: {stats['total']} 错误, 恢复率: {stats['recovery_rate']:.0%}")
    return stats


def example_tool_router():
    """ToolRouter 示例"""
    router = ToolRouter()

    # 注册工具
    router.register_batch([
        {"name": "search", "description": "搜索网络", "phase": "init"},
        {"name": "read_file", "description": "读取文件", "phase": "init"},
        {"name": "write_file", "description": "写入文件", "phase": "execute"},
        {"name": "execute_code", "description": "执行代码", "phase": "execute"},
        {"name": "analyze_data", "description": "分析数据", "phase": "explore"},
        {"name": "validate_result", "description": "验证结果", "phase": "review"},
    ])

    print(f"  初始阶段工具: {[t.name for t in router.get_active_tools()]}")

    router.set_phase(ToolPhase.EXECUTE)
    print(f"  执行阶段工具: {[t.name for t in router.get_active_tools()]}")

    router.use_tool("write_file")
    stats = router.get_stats()
    print(f"  总工具数: {stats['total_tools']}, 当前阶段: {stats['current_phase']}")
    return stats


def example_dashboard():
    """Dashboard 示例"""
    dash = Dashboard()

    # 记录指标
    for i in range(10):
        dash.record("cpu_usage", 45 + i * 2)
        dash.record("memory_usage", 60 + i)
        dash.record_tool_call("search", success=True, duration_ms=150 + i * 10)

    dash.record_tool_call("write_file", success=False, duration_ms=500)

    print(f"  CPU: last={dash.get_metric('cpu_usage').last:.1f}%")
    print(f"  Memory: last={dash.get_metric('memory_usage').last:.1f}%")
    print(f"  Tool errors: {dash.get_metric('tool.errors').last:.0f}")
    print(f"  运行时间: {dash.get_snapshot()['uptime_formatted']}")
    return dash.get_snapshot()


def example_access_control():
    """AccessControl 示例"""
    ac = AccessControl()
    ac.add_default_rules()

    checks = [
        ("read:workspace/data.csv", None),
        ("write:workspace/output.txt", None),
        ("delete:workspace/data.csv", None),
        ("execute:rm -rf /", None),
    ]

    for op, op_type in checks:
        result = ac.check(op, op_type)
        print(f"  {op:40s} → level={result['level']:10s} granted={result['granted']}")

    stats = ac.get_stats()
    print(f"  总检查: {stats['total_checks']}, 允许: {stats['granted']}, 拒绝: {stats['denied']}")
    return stats


def example_mcp_server():
    """MCPServer 示例（仅注册，不启动）"""
    server = MCPServer(port=8901)

    def search_handler(query: str) -> str:
        return f"搜索结果: {query}"

    def analyze_handler(data: str) -> str:
        return f"分析结果: {len(data)} 字符数据已分析"

    server.register_tool("search", "搜索网络信息", search_handler,
                         parameters={"type": "object", "properties": {
                             "query": {"type": "string", "description": "搜索关键词"}
                         }})
    server.register_tool("analyze", "分析数据", analyze_handler,
                         parameters={"type": "object", "properties": {
                             "data": {"type": "string", "description": "待分析数据"}
                         }})

    # 测试 RPC 请求
    list_req = server.handle_request({
        "jsonrpc": "2.0", "method": "list_tools", "id": "1"
    })
    print(f"  注册工具: {[t['name'] for t in list_req['result']['tools']]}")

    call_req = server.handle_request({
        "jsonrpc": "2.0", "method": "call_tool", "id": "2",
        "params": {"name": "search", "arguments": {"query": "AI Agent 2026"}}
    })
    print(f"  调用结果: {call_req['result']['content'][0]['text']}")

    stats = server.get_stats()
    print(f"  服务器状态: started={stats['started']}, tools={stats['tools_registered']}")
    return stats


if __name__ == "__main__":
    print("=" * 50)
    print("AutoAgentKit 示例")
    print("=" * 50)

    print("\n1️⃣ PlanMode — 计划执行模式")
    example_plan_mode()

    print("\n2️⃣ ErrorReflection — 错误反射")
    example_error_reflection()

    print("\n3️⃣ ToolRouter — 工具路由器")
    example_tool_router()

    print("\n4️⃣ Dashboard — 仪表板")
    example_dashboard()

    print("\n5️⃣ AccessControl — 访问控制")
    example_access_control()

    print("\n6️⃣ MCPServer — MCP 服务器")
    example_mcp_server()

    print("\n" + "=" * 50)
    print("所有示例运行完成 ✅")
    print("=" * 50)
