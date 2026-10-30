# -*- coding: utf-8 -*-
"""轻量变化检测：新观察 vs 现有记忆（规则相似），产出候选。"""

from __future__ import annotations

import re
from typing import Any

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryStatus, SearchQuery

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2}|[A-Za-z0-9_]{3,}")


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def detect_changes_for_observation(
    service: MemoryService,
    observation_id: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    conn = service.db.connect()
    row = conn.execute(
        "SELECT * FROM observations WHERE id=?", (observation_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "detail": "observation_not_found", "candidates": []}
    content = str(row["content"] or "")
    toks = _tokens(content)
    hits = service.search(SearchQuery(query=content[:80], limit=12))
    candidates: list[dict[str, Any]] = []
    for m in hits:
        if m.status == MemoryStatus.INVALIDATED:
            continue
        sim = _jaccard(toks, _tokens(m.content))
        if sim < 0.18:
            continue
        ctype = "continues"
        if any(k in content for k in ("不", "改了", "不再", "取消", "纠正")) and sim >= 0.25:
            ctype = "corrects"
        elif sim >= 0.55:
            ctype = "evolves"
        candidates.append(
            {
                "change_type": ctype,
                "memory_id": m.id,
                "confidence": round(min(0.9, 0.35 + sim), 3),
                "similarity": round(sim, 3),
                "reason": f"token_overlap={sim:.2f}",
                "memory_content_preview": m.content[:120],
                "suggested_relation": "contradicts" if ctype == "corrects" else "supports",
            }
        )
    return {
        "ok": True,
        "observation_id": observation_id,
        "dry_run": dry_run,
        "candidates": candidates,
        "count": len(candidates),
    }
