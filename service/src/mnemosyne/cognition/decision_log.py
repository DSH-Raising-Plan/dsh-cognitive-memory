# -*- coding: utf-8 -*-
"""认知决策日志（可解释晋升 / 降级 / 挂起）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mnemosyne.storage.db import Database
from mnemosyne.storage.ids import new_id

STRATEGY_VERSION = "promote_v2"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_decision(
    db: Database,
    *,
    subject_id: str,
    decision_type: str,
    outcome: str,
    evidence_ids: list[str] | None = None,
    scores: dict[str, Any] | None = None,
    reason: str = "",
    needs_human: bool = False,
    subject_kind: str = "memory",
    strategy_version: str = STRATEGY_VERSION,
) -> str:
    did = new_id("dec")
    now = _now()
    with db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO decision_logs(
              id, subject_id, subject_kind, decision_type, strategy_version,
              outcome, evidence_ids_json, scores_json, reason, needs_human, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                did,
                subject_id,
                subject_kind,
                decision_type,
                strategy_version,
                outcome,
                json.dumps(list(evidence_ids or []), ensure_ascii=False),
                json.dumps(scores or {}, ensure_ascii=False),
                reason or "",
                1 if needs_human else 0,
                now,
            ),
        )
    return did


def list_decisions(
    db: Database,
    *,
    subject_id: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    lim = max(1, min(200, int(limit or 40)))
    conn = db.connect()
    if subject_id:
        rows = conn.execute(
            """
            SELECT * FROM decision_logs
            WHERE subject_id=?
            ORDER BY created_at DESC LIMIT ?
            """,
            (subject_id, lim),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM decision_logs ORDER BY created_at DESC LIMIT ?",
            (lim,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "subject_id": r["subject_id"],
                "subject_kind": r["subject_kind"],
                "decision_type": r["decision_type"],
                "strategy_version": r["strategy_version"],
                "outcome": r["outcome"],
                "evidence_ids": json.loads(r["evidence_ids_json"] or "[]"),
                "scores": json.loads(r["scores_json"] or "{}"),
                "reason": r["reason"],
                "needs_human": bool(r["needs_human"]),
                "created_at": r["created_at"],
            }
        )
    return out
