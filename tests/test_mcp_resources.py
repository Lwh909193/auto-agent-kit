"""MCPServer Resources + Prompts 测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_agent_kit import MCPServer

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

server = MCPServer()

# ============ 1. 注册资源 ============
print("\n=== 1. 注册资源 ===")

server.register_resource(
    uri="knowledge://system/overview",
    name="System Overview",
    description="系统概览文档",
    handler=lambda: "# 系统概览\n\n这是 AutoAgentKit 的系统文档。",
    mime_type="text/markdown"
)

server.register_resource(
    uri="config://server/defaults",
    name="Server Defaults",
    description="服务器默认配置",
    handler=lambda: json.dumps({"host": "0.0.0.0", "port": 8901, "max_tools": 100}),
    mime_type="application/json"
)

test("资源注册数", len(server._resources) == 2)
test("资源 URI 正确", "knowledge://system/overview" in server._resources)
test("资源 MIME 类型", server._resources["knowledge://system/overview"].mime_type == "text/markdown")

# ============ 2. 注册资源模板 ============
print("\n=== 2. 注册资源模板 ===")

server.register_resource_template(
    uri_template="knowledge://{topic}",
    name="Knowledge Topic",
    description="按主题查询知识",
    handler=lambda params: f"# {params['topic']}\n\n这是关于 {params['topic']} 的知识。",
)

server.register_resource_template(
    uri_template="file://{path}",
    name="File Access",
    description="文件访问",
    handler=lambda params: f"File content: {params['path']}",
)

test("资源模板数", len(server._resource_templates) == 2)

# ============ 3. 解析资源 ============
print("\n=== 3. 解析资源 ===")

# 精确匹配
r1 = server._resolve_resource("knowledge://system/overview")
test("精确匹配", r1 is not None and "系统概览" in r1.handler())

# 模板匹配
r2 = server._resolve_resource("knowledge://python")
test("模板匹配", r2 is not None and "python" in r2.handler().lower())

r3 = server._resolve_resource("file:///etc/config.json")
test("文件模板", r3 is not None and "etc/config.json" in r3.handler())

# 不存在的资源
r4 = server._resolve_resource("unknown://uri")
test("不存在返回 None", r4 is None)

# ============ 4. 注册提示模板 ============
print("\n=== 4. 注册提示模板 ===")

server.register_prompt(
    name="analyze_code",
    description="分析代码质量",
    handler=lambda args: f"请分析以下 {args.get('language', 'unknown')} 代码的质量：\n\n```{args.get('language', '')}\n{args.get('code', '')}\n```\n\n关注：可读性、性能、安全性。",
    arguments=[
        {"name": "code", "description": "代码内容", "required": True},
        {"name": "language", "description": "编程语言", "required": False},
    ]
)

server.register_prompt(
    name="summarize",
    description="总结文本",
    handler=lambda args: f"请用 {args.get('style', '简洁')} 的风格总结以下内容：\n\n{args.get('text', '')}",
    arguments=[
        {"name": "text", "description": "要总结的文本", "required": True},
        {"name": "style", "description": "总结风格", "required": False},
    ]
)

test("提示模板数", len(server._prompts) == 2)
test("提示参数", len(server._prompts["analyze_code"].arguments) == 2)
test("必填参数", server._prompts["analyze_code"].arguments[0].required == True)
test("可选参数", server._prompts["analyze_code"].arguments[1].required == False)

# ============ 5. 提示模板执行 ============
print("\n=== 5. 提示模板执行 ===")

prompt = server._prompts["analyze_code"]
content = prompt.handler({"code": "print('hello')", "language": "python"})
test("提示模板输出", "python" in content and "print('hello')" in content)

prompt2 = server._prompts["summarize"]
content2 = prompt2.handler({"text": "很长的一段文字...", "style": "学术"})
test("带可选参数", "学术" in content2 and "很长的一段文字" in content2)

# ============ 6. JSON-RPC 请求处理 ============
print("\n=== 6. JSON-RPC 请求处理 ===")

# list_resources
resp = server.handle_request({"jsonrpc": "2.0", "method": "list_resources", "id": "1"})
test("list_resources 成功", "result" in resp)
test("resources 列表", len(resp["result"]["resources"]) == 2)
test("resourceTemplates 列表", len(resp["result"]["resourceTemplates"]) == 2)

# read_resource (精确)
resp2 = server.handle_request({
    "jsonrpc": "2.0", "method": "read_resource",
    "params": {"uri": "knowledge://system/overview"}, "id": "2"
})
test("read_resource 精确", "result" in resp2)
test("资源内容", "系统概览" in resp2["result"]["contents"][0]["text"])

# read_resource (模板)
resp3 = server.handle_request({
    "jsonrpc": "2.0", "method": "read_resource",
    "params": {"uri": "knowledge://python"}, "id": "3"
})
test("read_resource 模板", "result" in resp3)
test("模板内容", "python" in resp3["result"]["contents"][0]["text"].lower())

# read_resource (不存在)
resp4 = server.handle_request({
    "jsonrpc": "2.0", "method": "read_resource",
    "params": {"uri": "unknown://x"}, "id": "4"
})
test("read_resource 不存在", "error" in resp4)

# list_prompts
resp5 = server.handle_request({"jsonrpc": "2.0", "method": "list_prompts", "id": "5"})
test("list_prompts 成功", "result" in resp5)
test("prompts 列表", len(resp5["result"]["prompts"]) == 2)

# get_prompt
resp6 = server.handle_request({
    "jsonrpc": "2.0", "method": "get_prompt",
    "params": {"name": "analyze_code", "arguments": {"code": "x=1", "language": "python"}},
    "id": "6"
})
test("get_prompt 成功", "result" in resp6)
test("提示内容", "python" in resp6["result"]["messages"][0]["content"]["text"])

# get_prompt (不存在)
resp7 = server.handle_request({
    "jsonrpc": "2.0", "method": "get_prompt",
    "params": {"name": "nonexistent"}, "id": "7"
})
test("get_prompt 不存在", "error" in resp7)

# ============ 7. 批量注册 ============
print("\n=== 7. 批量注册 ===")

server2 = MCPServer()
server2.register_resources([
    {"uri": "doc://readme", "name": "README", "description": "项目说明",
     "handler": lambda: "# README", "mime_type": "text/markdown"},
    {"uri_template": "doc://{id}", "name": "Dynamic Doc",
     "description": "动态文档", "handler": lambda p: f"Doc {p['id']}"},
])
server2.register_prompts([
    {"name": "greet", "description": "问候", "handler": lambda a: f"Hello {a.get('name', 'world')}",
     "arguments": [{"name": "name", "description": "名字", "required": False}]},
])

test("批量注册资源", len(server2._resources) == 1)
test("批量注册模板", len(server2._resource_templates) == 1)
test("批量注册提示", len(server2._prompts) == 1)

# ============ 8. 统计信息 ============
print("\n=== 8. 统计信息 ===")

stats = server.get_stats()
test("统计包含 tools", "tools_registered" in stats)
test("统计包含 resources", "resources_registered" in stats)
test("统计包含 prompts", "prompts_registered" in stats)
test("统计包含 resource_templates", "resource_templates" in stats)
test("资源数正确", stats["resources_registered"] == 2)
test("模板数正确", stats["resource_templates"] == 2)
test("提示数正确", stats["prompts_registered"] == 2)

# ============ 9. 错误处理 ============
print("\n=== 9. 错误处理 ===")

# 资源 handler 出错
server3 = MCPServer()
server3.register_resource(
    uri="broken://resource",
    name="Broken",
    description="会出错的资源",
    handler=lambda: 1/0
)
resp_err = server3.handle_request({
    "jsonrpc": "2.0", "method": "read_resource",
    "params": {"uri": "broken://resource"}, "id": "1"
})
test("资源出错返回 error", "error" in resp_err)

# 提示 handler 出错
server3.register_prompt(
    name="broken_prompt",
    description="会出错的提示",
    handler=lambda args: 1/0
)
resp_err2 = server3.handle_request({
    "jsonrpc": "2.0", "method": "get_prompt",
    "params": {"name": "broken_prompt"}, "id": "2"
})
test("提示出错返回 error", "error" in resp_err2)

# ============ 10. 资源模板参数提取 ============
print("\n=== 10. 模板参数提取 ===")

server4 = MCPServer()
server4.register_resource_template(
    uri_template="api://{version}/{endpoint}",
    name="API Resource",
    description="API 资源",
    handler=lambda params: f"version={params['version']}, endpoint={params['endpoint']}",
)

r_multi = server4._resolve_resource("api://v2/users")
test("多参数模板", r_multi is not None)
test("多参数内容", "version=v2" in r_multi.handler() and "endpoint=users" in r_multi.handler())

# ============ 总结 ============
print(f"\n{'='*40}")
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 测试")
print(f"{'='*40}")

sys.exit(0 if failed == 0 else 1)
