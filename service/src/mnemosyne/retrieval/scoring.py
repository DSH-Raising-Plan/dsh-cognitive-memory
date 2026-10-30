# -*- coding: utf-8 -*-
"""可解释排序：Score = wr*R + wt*T + ws*S + we*E（无外置向量依赖）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from mnemosyne.domain.models import Memory, MemoryStatus

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2}|[A-Za-z0-9_]{3,}")
DEFAULT_WEIGHTS = {"r": 0.45, "t": 0.20, "s": 0.20, "e": 0.15}


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def relevance_score(content: str, query: str) -> float:
    qt, ct = _tokens(query), _tokens(content)
    if not qt or not ct:
        q = (query or "").strip().lower()
        c = (content or "").strip().lower()
        if not q or not c:
            return 0.0
        return 1.0 if q in c else 0.0
    return min(1.0, len(qt & ct) / max(1, len(qt)))


def status_score(status: MemoryStatus | str) -> float:
    s = status.value if isinstance(status, MemoryStatus) else str(status or "")
    return {
        "active": 1.0,
        "candidate": 0.55,
        "superseded": 0.15,
        "invalidated": 0.0,
    }.get(s, 0.3)


def evidence_score(memory: Memory) -> float:
    n = len(memory.source_ids or [])
    if n <= 0:
        return 0.35
    if n == 1:
        return 0.55
    if n == 2:
        return 0.75
    return 1.0


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def temporal_score(memory: Memory, *, mode: str = "current") -> float:
    """简单时效分：过期降权；historical 偏旧条目。"""
    now = datetime.now(timezone.utc)
    exp = _parse_ts(memory.expires_at)
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and exp < now and mode == "current":
        return 0.15
    updated = _parse_ts(memory.updated_at) or _parse_ts(memory.created_at)
    if not updated:
        return 0.5
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - updated).total_seconds() / 86400.0)
    freshness = max(0.2, 1.0 - min(age_days, 365.0) / 365.0)
    if mode == "historical":
        return max(0.3, 1.0 - freshness * 0.5)
    if mode == "any":
        return 0.55 + 0.45 * freshness
    return freshness


def score_memory(
    memory: Memory,
    query: str,
    *,
    mode: str = "current",
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    r = relevance_score(memory.content, query)
    t = temporal_score(memory, mode=mode)
    s = status_score(memory.status)
    e = evidence_score(memory)
    total = w["r"] * r + w["t"] * t + w["s"] * s + w["e"] * e
    return {
        "total": round(total, 4),
        "R": round(r, 4),
        "T": round(t, 4),
        "S": round(s, 4),
        "E": round(e, 4),
        "weights": w,
    }
