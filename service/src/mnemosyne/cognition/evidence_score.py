# -*- coding: utf-8 -*-
"""证据聚合：支持/反证计数与来源独立性（非固定心理学常数）。"""

from __future__ import annotations

from typing import Any


SUPPORTING = frozenset({"supports", "derives"})
CONTRADICTING = frozenset({"contradicts"})


def independence_key(ev: dict[str, Any]) -> str:
    """同一会话/同一次发言拆出的多条观察不算独立来源。"""
    prov = dict(ev.get("provenance") or {})
    corr = prov.get("correlation_id") or ev.get("correlation_id") or ""
    producer = prov.get("producer") or ev.get("producer") or ""
    source_kind = prov.get("source_kind") or ev.get("source_kind") or ""
    source_id = str(ev.get("source_id") or ev.get("observation_id") or "")
    if corr:
        return f"corr:{corr}|{producer}|{source_kind}"
    return f"src:{source_id}|{producer}|{source_kind}"


def score_evidence(items: list[dict[str, Any]]) -> dict[str, Any]:
    support_items = [
        e for e in items if str(e.get("evidence_type") or e.get("relation") or "supports").lower() in SUPPORTING
    ]
    counter_items = [
        e
        for e in items
        if str(e.get("evidence_type") or e.get("relation") or "").lower() in CONTRADICTING
    ]
    support_keys = {independence_key(e) for e in support_items}
    counter_keys = {independence_key(e) for e in counter_items}
    return {
        "support_count": len(support_items),
        "counter_count": len(counter_items),
        "independent_support_sources": len(support_keys),
        "independent_counter_sources": len(counter_keys),
        "support_keys": sorted(support_keys),
        "counter_keys": sorted(counter_keys),
        "evidence_ids": [str(e.get("id") or e.get("observation_id") or "") for e in items],
    }


def evaluate_promotion(
    scores: dict[str, Any],
    *,
    meta: dict[str, Any] | None = None,
    memory_type: str = "semantic",
) -> dict[str, Any]:
    """可配置门槛：默认需 ≥2 独立支持源，且无强反证；force / from_user 可短路。"""
    meta = meta or {}
    if meta.get("force_activate"):
        return {
            "decision": "promote",
            "outcome": "active",
            "reason": "force_activate",
            "needs_human": False,
        }
    if memory_type == "semantic" and meta.get("from_user") is True and scores["counter_count"] == 0:
        return {
            "decision": "promote",
            "outcome": "active",
            "reason": "explicit_user_statement",
            "needs_human": False,
        }
    if scores["independent_counter_sources"] >= 1 and scores["counter_count"] >= 1:
        # 强反证：挂起而非抹掉正向证据
        return {
            "decision": "needs_review",
            "outcome": "needs_review",
            "reason": "counter_evidence_present",
            "needs_human": True,
        }
    min_indep = int(meta.get("min_independent_sources") or 2)
    if scores["independent_support_sources"] >= min_indep:
        return {
            "decision": "promote",
            "outcome": "active",
            "reason": f"independent_support>={min_indep}",
            "needs_human": False,
        }
    if scores["support_count"] >= 2 and scores["independent_support_sources"] < 2:
        return {
            "decision": "hold",
            "outcome": "candidate",
            "reason": "duplicate_sources_not_independent",
            "needs_human": False,
        }
    return {
        "decision": "hold",
        "outcome": "candidate",
        "reason": "insufficient_independent_support",
        "needs_human": False,
    }
