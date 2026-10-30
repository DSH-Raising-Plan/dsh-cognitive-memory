# -*- coding: utf-8 -*-
"""分层检索管线：plan → recall → filter → score → optional deepen。"""

from __future__ import annotations

import time
import traceback
from typing import Any

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import ContextBuildIn, Memory, MemoryStatus, SearchQuery
from mnemosyne.retrieval.planner import QueryPlan, plan_retrieval
from mnemosyne.retrieval.scoring import score_memory

RESULT_FOUND = "FOUND"
RESULT_PARTIAL = "PARTIAL"
RESULT_NO_MATCH = "NO_MATCH"
RESULT_FAILED = "FAILED"
RESULT_NOT_NEEDED = "NOT_NEEDED"


def _filter_candidates(
    memories: list[Memory],
    plan: QueryPlan,
    *,
    session_id: str | None = None,
) -> list[Memory]:
    out: list[Memory] = []
    for m in memories:
        if m.status == MemoryStatus.INVALIDATED:
            continue
        if plan.mode == "current" and m.status == MemoryStatus.SUPERSEDED:
            continue
        if session_id:
            meta = m.metadata if isinstance(m.metadata, dict) else {}
            sid = str(meta.get("session_id") or "")
            # 有 session 标记时隔离；无标记视为可共享（兼容旧数据）
            if sid and sid != session_id:
                continue
        out.append(m)
    return out


def _rank(
    memories: list[Memory],
    query: str,
    *,
    mode: str,
) -> list[tuple[Memory, dict[str, Any]]]:
    scored: list[tuple[Memory, dict[str, Any]]] = []
    for m in memories:
        scored.append((m, score_memory(m, query, mode=mode)))
    scored.sort(key=lambda x: x[1]["total"], reverse=True)
    return scored


def run_retrieve(
    service: MemoryService,
    *,
    query: str,
    force: bool = False,
    limit: int = 8,
    mode: str = "current",
    token_budget: int | None = None,
    types: list | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    plan = plan_retrieval(
        query,
        force=force,
        default_mode=mode,
        default_limit=limit,
    )
    trace: dict[str, Any] = {
        "plan": plan.to_dict(),
        "channels": [],
        "deepened": False,
        "session_id": session_id,
        "error": None,
    }

    if not plan.should_retrieve:
        return {
            "status": RESULT_NOT_NEEDED,
            "plan": plan.to_dict(),
            "items": [],
            "count": 0,
            "brief": "",
            "fragments": [],
            "token_estimate": 0,
            "retrieval_ready": False,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
        }

    try:
        fetch_n = max(plan.limit, min(40, plan.limit * 2))
        hits = service.search(
            SearchQuery(query=query, types=types, limit=fetch_n)
        )
        trace["channels"].append({"name": "fts_like", "raw_hits": len(hits)})
        filtered = _filter_candidates(hits, plan, session_id=session_id)
        ranked = _rank(filtered, query, mode=plan.mode)

        if len(ranked) < plan.expected_min_hits and plan.depth in ("normal", "deep"):
            deep_hits = service.search(
                SearchQuery(query=query, types=types, limit=min(50, fetch_n * 2))
            )
            trace["deepened"] = True
            trace["channels"].append({"name": "deepen", "raw_hits": len(deep_hits)})
            seen = {m.id for m, _ in ranked}
            for m in _filter_candidates(deep_hits, plan, session_id=session_id):
                if m.id not in seen:
                    ranked.append((m, score_memory(m, query, mode="any")))
                    seen.add(m.id)
            ranked.sort(key=lambda x: x[1]["total"], reverse=True)

        ranked = ranked[: plan.limit]
        items = []
        for m, sc in ranked:
            items.append(
                {
                    "id": m.id,
                    "type": m.type.value,
                    "status": m.status.value,
                    "content": m.content,
                    "version": m.version,
                    "source_ids": m.source_ids,
                    "score": sc,
                    "metadata": m.metadata,
                }
            )

        ctx = service.build_context(
            ContextBuildIn(
                query=query,
                token_budget=token_budget,
                types=types,
                limit=plan.limit,
            )
        )

        if not items:
            status = RESULT_NO_MATCH
        elif len(items) < plan.expected_min_hits or (
            items and items[0]["score"]["total"] < 0.25
        ):
            status = RESULT_PARTIAL
        else:
            status = RESULT_FOUND

        # brief：仅用命中 items，避免 build_context 再搜引入未过滤结果
        lines = ["【演化记忆·仅供参考】"]
        fragments = []
        used = 0
        budget = token_budget or service.context_token_budget
        for it in items:
            est = max(1, len(it["content"]) // 2)
            if used + est > budget and fragments:
                break
            frag = {
                "id": it["id"],
                "type": it["type"],
                "status": it["status"],
                "content": it["content"],
                "version": it["version"],
                "source_ids": it["source_ids"],
                "token_estimate": est,
                "score": it["score"],
            }
            fragments.append(frag)
            used += est
            lines.append(f"- [{it['type']}] {it['content']}")

        return {
            "status": status,
            "plan": plan.to_dict(),
            "items": items,
            "count": len(items),
            "brief": "\n".join(lines) if items else "",
            "fragments": fragments,
            "token_estimate": used,
            "retrieval_ready": True,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
            "context_fallback_brief": ctx.brief if not items else None,
        }
    except Exception as exc:
        trace["error"] = f"{type(exc).__name__}: {exc}"
        trace["traceback"] = traceback.format_exc(limit=3)
        return {
            "status": RESULT_FAILED,
            "plan": plan.to_dict(),
            "items": [],
            "count": 0,
            "brief": "",
            "fragments": [],
            "token_estimate": 0,
            "retrieval_ready": False,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
            "error": str(exc),
        }
