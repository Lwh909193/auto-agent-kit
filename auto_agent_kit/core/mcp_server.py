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

        # 内置方法
        if req.method == "list_tools":
            return req.to_response(result={
                "tools": [
                    {"name": t.name, "description": t.description, "parameters": t.parameters}
                    for t in self._tools.values()
                ]
            })

        if req.method == "ping":
            return req.to_response(result={"pong": True, "timestamp": time.time()})

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
            "requests_handled": len(self._request_log),
            "tool_names": list(self._tools.keys()),
        }

    def stop(self):
        """停止服务器"""
        self._started = False
        logger.info("MCP Server stopped")
