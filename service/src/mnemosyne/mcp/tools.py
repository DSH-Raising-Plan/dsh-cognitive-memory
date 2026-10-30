# -*- coding: utf-8 -*-
"""MCP / Host 共用工具清单与分发（协议层只做转换）。"""

from __future__ import annotations

from typing import Any

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import (
    ContextBuildIn,
    FeedbackIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    MemoryUpdateIn,
    ObservationIn,
    SearchQuery,
    SourceKind,
)

TOOL_NAMES = [
    "memory_health",
    "memory_search",
    "memory_get",
    "memory_context",
    "memory_retrieve",
    "memory_propose",
    "memory_update",
    "memory_forget",
    "memory_observe",
    "memory_feedback",
    "memory_task_status",
]


def tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "memory_health",
            "description": "Memory service health",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "memory_search",
            "description": "Search memories (FTS5, LIKE fallback)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "types": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_get",
            "description": "Get memory detail and evidence",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "include_evidence": {"type": "boolean"},
                },
                "required": ["id"],
            },
        },
        {
            "name": "memory_context",
            "description": "Build context within a token budget",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "token_budget": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_retrieve",
            "description": "Planned retrieve with hit/miss status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "force": {"type": "boolean"},
                    "limit": {"type": "integer"},
                    "mode": {"type": "string"},
                    "token_budget": {"type": "integer"},
                    "session_id": {"type": "string"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_propose",
            "description": "Propose a candidate memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "type": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content"],
            },
        },
        {
            "name": "memory_update",
            "description": "Update memory (supports expected_version)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "content": {"type": "string"},
                    "status": {"type": "string"},
                    "expected_version": {"type": "integer"},
                },
                "required": ["id"],
            },
        },
        {
            "name": "memory_forget",
            "description": "Invalidate or hard-forget a memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "hard": {"type": "boolean"},
                },
                "required": ["id"],
            },
        },
        {
            "name": "memory_observe",
            "description": "Capture an observation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "source_kind": {"type": "string"},
                    "producer": {"type": "string"},
                    "correlation_id": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                },
                "required": ["content"],
            },
        },
        {
            "name": "memory_feedback",
            "description": "Feedback useful/incorrect on a memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "useful": {"type": "boolean"},
                    "incorrect": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["memory_id"],
            },
        },
        {
            "name": "memory_task_status",
            "description": "Get background task status",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
    ]


def dispatch_tool(service: MemoryService, name: str, args: dict[str, Any]) -> Any:
    if name == "memory_health":
        return service.health()
    if name == "memory_search":
        types = None
        if args.get("types"):
            types = [MemoryType(t) for t in args["types"]]
        rows = service.search(
            SearchQuery(
                query=args.get("query") or "",
                limit=int(args.get("limit") or 10),
                types=types,
            )
        )
        return {"items": [m.model_dump() for m in rows]}
    if name == "memory_get":
        return service.get_memory(
            args["id"], include_evidence=bool(args.get("include_evidence"))
        )
    if name == "memory_context":
        return service.build_context(
            ContextBuildIn(query=args["query"], token_budget=args.get("token_budget"))
        ).model_dump()
    if name == "memory_retrieve":
        from mnemosyne.retrieval.pipeline import run_retrieve

        return run_retrieve(
            service,
            query=args.get("query") or "",
            force=bool(args.get("force")),
            limit=int(args.get("limit") or 8),
            mode=str(args.get("mode") or "current"),
            token_budget=args.get("token_budget"),
            session_id=args.get("session_id"),
        )
    if name == "memory_propose":
        return service.propose_memory(
            MemoryProposeIn(
                content=args["content"],
                type=MemoryType(args["type"]) if args.get("type") else MemoryType.SEMANTIC,
                source_ids=list(args.get("source_ids") or []),
            )
        ).model_dump()
    if name == "memory_update":
        return service.update_memory(
            args["id"],
            MemoryUpdateIn(
                content=args.get("content"),
                status=MemoryStatus(args["status"]) if args.get("status") else None,
                expected_version=args.get("expected_version"),
            ),
        ).model_dump()
    if name == "memory_forget":
        return service.forget_memory(args["id"], hard=bool(args.get("hard")))
    if name == "memory_observe":
        kind = args.get("source_kind") or "dialog"
        return service.capture_observation(
            ObservationIn(
                content=args["content"],
                source_kind=SourceKind(kind) if kind in SourceKind._value2member_map_ else SourceKind.DIALOG,
                producer=args.get("producer") or "mcp",
                correlation_id=args.get("correlation_id"),
                idempotency_key=args.get("idempotency_key"),
            )
        ).model_dump()
    if name == "memory_feedback":
        return service.feedback(
            FeedbackIn(
                memory_id=args["memory_id"],
                useful=args.get("useful"),
                incorrect=args.get("incorrect"),
                note=args.get("note") or "",
            )
        )
    if name == "memory_task_status":
        return service.get_task(args["id"]).model_dump()
    raise ValueError(f"unknown tool: {name}")
