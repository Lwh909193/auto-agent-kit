"""MCPServer — MCP 协议服务器

JSON-RPC 2.0 + SSE 传输，用于 Agent 工具暴露和远程调用。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("auto_agent_kit.mcp")


@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str
    handler: Callable
    mime_type: str = "text/plain"


@dataclass
class MCPResourceTemplate:
    """MCP 资源模板定义"""
    uri_template: str
    name: str
    description: str
    handler: Callable
    mime_type: str = "text/plain"


@dataclass
class MCPPromptArgument:
    """MCP 提示模板参数"""
    name: str
    description: str
    required: bool = False


@dataclass
class MCPPrompt:
    """MCP 提示模板定义"""
    name: str
    description: str
    handler: Callable
    arguments: list[MCPPromptArgument] = field(default_factory=list)


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    handler: Callable
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass
class MCPRequest:
    """JSON-RPC 请求"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Any = None
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MCPRequest":
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
        )

    def to_response(self, result: Any = None, error: Optional[dict] = None) -> dict:
        resp = {"jsonrpc": "2.0", "id": self.id}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        return resp


class MCPServer:
    """MCP 协议服务器 — JSON-RPC 2.0 + SSE"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8901):
        self.host = host
        self.port = port
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._resource_templates: list[MCPResourceTemplate] = []
        self._prompts: dict[str, MCPPrompt] = {}
        self._request_log: list[dict] = []
        self._max_log: int = 500
        self._app: Any = None  # FastAPI app (lazy init)
        self._started: bool = False

    def register_tool(self, name: str, description: str, handler: Callable,
                      parameters: Optional[dict] = None):
        """注册一个 MCP 工具"""
        self._tools[name] = MCPTool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {"type": "object", "properties": {}},
        )

    def register_tools(self, tools: list[dict]):
        """批量注册工具"""
        for t in tools:
            self.register_tool(
                name=t["name"],
                description=t.get("description", ""),
                handler=t["handler"],
                parameters=t.get("parameters"),
            )

    # ---- 资源管理 ----

    def register_resource(self, uri: str, name: str, description: str, handler: Callable,
                          mime_type: str = "text/plain"):
        """注册一个 MCP 资源"""
        self._resources[uri] = MCPResource(
            uri=uri, name=name, description=description,
            handler=handler, mime_type=mime_type,
        )

    def register_resource_template(self, uri_template: str, name: str, description: str,
                                    handler: Callable, mime_type: str = "text/plain"):
        """注册一个 MCP 资源模板"""
        self._resource_templates.append(MCPResourceTemplate(
            uri_template=uri_template, name=name, description=description,
            handler=handler, mime_type=mime_type,
        ))

    def register_resources(self, resources: list[dict]):
        """批量注册资源"""
        for r in resources:
            if "uri" in r:
                self.register_resource(
                    uri=r["uri"], name=r["name"], description=r.get("description", ""),
                    handler=r["handler"], mime_type=r.get("mime_type", "text/plain"),
                )
            elif "uri_template" in r:
                self.register_resource_template(
                    uri_template=r["uri_template"], name=r["name"],
                    description=r.get("description", ""),
                    handler=r["handler"], mime_type=r.get("mime_type", "text/plain"),
                )

    def _resolve_resource(self, uri: str) -> Optional[MCPResource]:
        """解析资源 URI，支持精确匹配和模板匹配"""
        # 精确匹配
        if uri in self._resources:
            return self._resources[uri]
        # 模板匹配
        import re
        for template in self._resource_templates:
            # 将 {param} 转换为命名捕获组（非贪婪匹配，支持斜杠）
            pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>.+?)", template.uri_template)
            match = re.fullmatch(pattern, uri)
            if match:
                params = match.groupdict()
                # 创建闭包捕获当前 handler 和 params
                handler = template.handler
                mime_type = template.mime_type
                wrapped = MCPResource(
                    uri=uri,
                    name=template.name,
                    description=template.description,
                    handler=lambda p=params, h=handler: h(p),
                    mime_type=mime_type,
                )
                return wrapped
        return None

    # ---- 提示模板管理 ----

    def register_prompt(self, name: str, description: str, handler: Callable,
                        arguments: Optional[list[dict]] = None):
        """注册一个 MCP 提示模板"""
        args = []
        if arguments:
            for a in arguments:
                args.append(MCPPromptArgument(
                    name=a["name"],
                    description=a.get("description", ""),
                    required=a.get("required", False),
                ))
        self._prompts[name] = MCPPrompt(
            name=name, description=description, handler=handler, arguments=args,
        )

    def register_prompts(self, prompts: list[dict]):
        """批量注册提示模板"""
        for p in prompts:
            self.register_prompt(
                name=p["name"], description=p.get("description", ""),
                handler=p["handler"], arguments=p.get("arguments"),
            )

    def handle_request(self, raw: dict) -> dict:
        """处理 JSON-RPC 请求"""
        try:
            req = MCPRequest.from_dict(raw)
        except Exception as e:
            return {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32700, "message": f"Parse error: {e}"
            }}

        # 记录请求
        self._request_log.append({
            "timestamp": time.time(),
            "method": req.method,
            "id": req.id,
        })
        if len(self._request_log) > self._max_log:
            self._request_log = self._request_log[-self._max_log:]

        # 内置方法 — 工具
        if req.method == "list_tools":
            return req.to_response(result={
                "tools": [
                    {"name": t.name, "description": t.description, "parameters": t.parameters}
                    for t in self._tools.values()
                ]
            })

        if req.method == "ping":
            return req.to_response(result={"pong": True, "timestamp": time.time()})

        # 内置方法 — 资源
        if req.method == "list_resources":
            resources_list = [
                {"uri": r.uri, "name": r.name, "description": r.description,
                 "mimeType": r.mime_type}
                for r in self._resources.values()
            ]
            templates_list = [
                {"uriTemplate": t.uri_template, "name": t.name, "description": t.description}
                for t in self._resource_templates
            ]
            return req.to_response(result={
                "resources": resources_list,
                "resourceTemplates": templates_list,
            })

        if req.method == "read_resource":
            uri = req.params.get("uri", "") if req.params else ""
            resource = self._resolve_resource(uri)
            if not resource:
                return req.to_response(error={
                    "code": -32602,
                    "message": f"Resource not found: {uri}",
                })
            try:
                content = resource.handler()
                return req.to_response(result={
                    "contents": [{
                        "uri": resource.uri,
                        "mimeType": resource.mime_type,
                        "text": str(content),
                    }]
                })
            except Exception as e:
                return req.to_response(error={
                    "code": -32000,
                    "message": f"Resource read error: {e}",
                })

        # 内置方法 — 提示模板
        if req.method == "list_prompts":
            return req.to_response(result={
                "prompts": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "arguments": [
                            {"name": a.name, "description": a.description,
                             "required": a.required}
                            for a in p.arguments
                        ],
                    }
                    for p in self._prompts.values()
                ]
            })

        if req.method == "get_prompt":
            prompt_name = req.params.get("name", "") if req.params else ""
            prompt_args = req.params.get("arguments", {}) if req.params else {}
            prompt = self._prompts.get(prompt_name)
            if not prompt:
                return req.to_response(error={
                    "code": -32602,
                    "message": f"Prompt not found: {prompt_name}",
                })
            try:
                content = prompt.handler(prompt_args)
                return req.to_response(result={
                    "messages": [{"role": "user", "content": {"type": "text", "text": str(content)}}]
                })
            except Exception as e:
                return req.to_response(error={
                    "code": -32000,
                    "message": f"Prompt execution error: {e}",
                })

        # 工具调用
        if req.method == "call_tool":
            tool_name = req.params.get("name", "") if req.params else ""
            tool_args = req.params.get("arguments", {}) if req.params else {}

            tool = self._tools.get(tool_name)
            if not tool:
                return req.to_response(error={
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}",
                })

            try:
                result = tool.handler(**tool_args)
                return req.to_response(result={
                    "content": [{"type": "text", "text": str(result)}],
                })
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return req.to_response(error={
                    "code": -32000,
                    "message": f"Tool execution error: {e}",
                })

        # 未知方法
        return req.to_response(error={
            "code": -32601,
            "message": f"Method not found: {req.method}",
        })

    def build_app(self):
        """构建 FastAPI 应用（可选依赖）"""
        try:
            from fastapi import FastAPI, Request
            from fastapi.responses import JSONResponse, StreamingResponse
        except ImportError:
            raise ImportError("FastAPI is required for MCPServer HTTP mode. "
                              "Install: pip install auto-agent-kit[mcp]")

        app = FastAPI(title="AutoAgentKit MCP Server", version="0.1.0")

        @app.get("/health")
        async def health():
            return {"status": "ok", "tools": len(self._tools)}

        @app.get("/tools")
        async def list_tools():
            return {
                "tools": [
                    {"name": t.name, "description": t.description}
                    for t in self._tools.values()
                ]
            }

        @app.get("/resources")
        async def list_resources():
            return {
                "resources": [
                    {"uri": r.uri, "name": r.name, "description": r.description,
                     "mimeType": r.mime_type}
                    for r in self._resources.values()
                ],
                "resourceTemplates": [
                    {"uriTemplate": t.uri_template, "name": t.name}
                    for t in self._resource_templates
                ]
            }

        @app.get("/prompts")
        async def list_prompts():
            return {
                "prompts": [
                    {"name": p.name, "description": p.description}
                    for p in self._prompts.values()
                ]
            }

        @app.post("/rpc")
        async def rpc(request: Request):
            body = await request.json()
            result = self.handle_request(body)
            return JSONResponse(result)

        @app.get("/sse")
        async def sse(request: Request):
            """SSE 端点"""
            async def event_generator():
                yield f"data: {json.dumps({'type': 'connected', 'tools': len(self._tools)})}\n\n"
                # 保持连接
                while True:
                    await asyncio.sleep(30)
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        self._app = app
        return app

    def start(self, host: Optional[str] = None, port: Optional[int] = None):
        """启动 MCP 服务器"""
        import asyncio
        import uvicorn

        host = host or self.host
        port = port or self.port

        app = self.build_app()
        self._started = True
        logger.info(f"MCP Server starting on {host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="info")

    def start_async(self, host: Optional[str] = None, port: Optional[int] = None):
        """异步启动（在已有事件循环中使用）"""
        import asyncio
        import uvicorn

        host = host or self.host
        port = port or self.port

        app = self.build_app()
        self._started = True

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        return server.serve()

    def get_stats(self) -> dict:
        """获取服务器统计"""
        return {
            "started": self._started,
            "host": self.host,
            "port": self.port,
            "tools_registered": len(self._tools),
            "resources_registered": len(self._resources),
            "resource_templates": len(self._resource_templates),
            "prompts_registered": len(self._prompts),
            "requests_handled": len(self._request_log),
            "tool_names": list(self._tools.keys()),
            "resource_uris": list(self._resources.keys()),
            "prompt_names": list(self._prompts.keys()),
        }

    def stop(self):
        """停止服务器"""
        self._started = False
        logger.info("MCP Server stopped")
