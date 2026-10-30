# -*- coding: utf-8 -*-
"""MCP 入口：优先官方 SDK；否则兼容 JSON-RPC stdio（测试 / 无依赖环境）。"""

from __future__ import annotations

import json
import sys
from typing import Any

from mnemosyne.core.service import ConflictError, MemoryService, NotFoundError
from mnemosyne.mcp.tools import dispatch_tool, tool_specs


def run_mcp_stdio(service: MemoryService) -> None:
    if _try_official_sdk(service):
        return
    _run_jsonrpc_fallback(service)


def _try_official_sdk(service: MemoryService) -> bool:
    """若已安装 mcp 包则用官方 Server；失败则回退。"""
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception:
        try:
            from mcp.server import Server  # type: ignore
            from mcp.server.stdio import stdio_server  # type: ignore
            from mcp import types as mcp_types  # type: ignore
        except Exception:
            return False
        return _run_lowlevel_sdk(service, Server, stdio_server, mcp_types)

    mcp = FastMCP("mnemosyne")

    @mcp.tool()
    def memory_health() -> dict[str, Any]:
        return dispatch_tool(service, "memory_health", {})

    @mcp.tool()
    def memory_search(query: str, limit: int = 10) -> dict[str, Any]:
        return dispatch_tool(service, "memory_search", {"query": query, "limit": limit})

    @mcp.tool()
    def memory_get(id: str, include_evidence: bool = False) -> dict[str, Any]:
        return dispatch_tool(
            service, "memory_get", {"id": id, "include_evidence": include_evidence}
        )

    @mcp.tool()
    def memory_context(query: str, token_budget: int | None = None) -> dict[str, Any]:
        return dispatch_tool(
            service, "memory_context", {"query": query, "token_budget": token_budget}
        )

    @mcp.tool()
    def memory_retrieve(
        query: str,
        force: bool = False,
        limit: int = 8,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return dispatch_tool(
            service,
            "memory_retrieve",
            {"query": query, "force": force, "limit": limit, "session_id": session_id},
        )

    @mcp.tool()
    def memory_propose(content: str, type: str = "semantic") -> dict[str, Any]:
        return dispatch_tool(
            service, "memory_propose", {"content": content, "type": type}
        )

    @mcp.tool()
    def memory_observe(content: str, source_kind: str = "dialog") -> dict[str, Any]:
        return dispatch_tool(
            service,
            "memory_observe",
            {"content": content, "source_kind": source_kind},
        )

    @mcp.tool()
    def memory_forget(id: str, hard: bool = False) -> dict[str, Any]:
        return dispatch_tool(service, "memory_forget", {"id": id, "hard": hard})

    @mcp.tool()
    def memory_feedback(
        memory_id: str,
        useful: bool | None = None,
        incorrect: bool | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        return dispatch_tool(
            service,
            "memory_feedback",
            {
                "memory_id": memory_id,
                "useful": useful,
                "incorrect": incorrect,
                "note": note,
            },
        )

    mcp.run(transport="stdio")
    return True


def _run_lowlevel_sdk(service: MemoryService, Server: Any, stdio_server: Any, mcp_types: Any) -> bool:
    import anyio

    server = Server("mnemosyne")

    @server.list_tools()
    async def list_tools() -> list[Any]:
        out = []
        for t in tool_specs():
            out.append(
                mcp_types.Tool(
                    name=t["name"],
                    description=t.get("description") or "",
                    inputSchema=t.get("inputSchema") or {"type": "object"},
                )
            )
        return out

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[Any]:
        data = dispatch_tool(service, name, arguments or {})
        text = json.dumps(data, ensure_ascii=False)
        return [mcp_types.TextContent(type="text", text=text)]

    async def _main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(_main)
    return True


def _run_jsonrpc_fallback(service: MemoryService) -> None:
    """极简 MCP-ish JSON-RPC over stdio（无官方 SDK 时使用）。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        try:
            if method == "tools/list":
                result = {"tools": tool_specs()}
            elif method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                data = dispatch_tool(service, name, arguments)
                result = {
                    "content": [
                        {"type": "text", "text": json.dumps(data, ensure_ascii=False)}
                    ]
                }
            elif method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "mnemosyne", "version": "0.3.3"},
                    "capabilities": {"tools": {}},
                }
            else:
                raise ValueError(f"unsupported method: {method}")
            resp = {"jsonrpc": "2.0", "id": rid, "result": result}
        except (NotFoundError, ConflictError, ValueError, KeyError) as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32000, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
