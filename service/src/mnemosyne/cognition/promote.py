# -*- coding: utf-8 -*-
"""慢速通道：候选晋升（promote_v2：独立性 + 反证 → Decision Log）。"""

from __future__ import annotations

from typing import Any

from mnemosyne.cognition.decision_log import write_decision
from mnemosyne.cognition.evidence_score import evaluate_promotion, score_evidence
from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryStatus, MemoryUpdateIn


def maybe_promote(service: MemoryService, memory_id: str) -> bool:
    result = evaluate_and_apply(service, memory_id)
    return bool(result.get("applied"))


def evaluate_and_apply(service: MemoryService, memory_id: str) -> dict[str, Any]:
    if not memory_id:
        return {"ok": False, "detail": "missing_memory_id"}
    data = service.get_memory(memory_id, include_evidence=True)
    status = data.get("status")
    if status not in (MemoryStatus.CANDIDATE.value, MemoryStatus.NEEDS_REVIEW.value):
        return {"ok": False, "detail": "not_promotable", "status": status}

    evidence_rows = service.list_evidence(subject_kind="memory", subject_id=memory_id)
    # 兼容旧 memory_evidence 行
    if not evidence_rows:
        for e in data.get("evidence") or []:
            evidence_rows.append(
                {
                    "id": e.get("observation_id"),
                    "source_id": e.get("observation_id"),
                    "observation_id": e.get("observation_id"),
                    "evidence_type": e.get("relation") or "supports",
                    "relation": e.get("relation") or "supports",
                    "provenance": {},
                }
            )
    # 补齐 observation 来源信息用于独立性
    enriched: list[dict[str, Any]] = []
    for e in evidence_rows:
        row = dict(e)
        sid = str(row.get("source_id") or row.get("observation_id") or "")
        if sid and row.get("source_type", "observation") == "observation":
            obs = service.get_observation(sid)
            if obs:
                prov = dict(row.get("provenance") or {})
                prov.setdefault("producer", obs.get("producer"))
                prov.setdefault("correlation_id", obs.get("correlation_id"))
                prov.setdefault("source_kind", obs.get("source_kind"))
                row["provenance"] = prov
                row["producer"] = obs.get("producer")
                row["correlation_id"] = obs.get("correlation_id")
                row["source_kind"] = obs.get("source_kind")
        enriched.append(row)

    scores = score_evidence(enriched)
    meta = data.get("metadata") or {}
    judgment = evaluate_promotion(
        scores, meta=meta, memory_type=str(data.get("type") or "semantic")
    )
    decision_id = write_decision(
        service.db,
        subject_id=memory_id,
        decision_type="promote_check",
        outcome=judgment["outcome"],
        evidence_ids=[x for x in scores.get("evidence_ids") or [] if x],
        scores={**scores, "judgment": judgment},
        reason=judgment.get("reason") or "",
        needs_human=bool(judgment.get("needs_human")),
    )

    applied = False
    new_status = None
    if judgment["decision"] == "promote":
        new_status = MemoryStatus.ACTIVE
    elif judgment["decision"] == "needs_review":
        new_status = MemoryStatus.NEEDS_REVIEW

    if new_status and new_status.value != status:
        service.update_memory(
            memory_id,
            MemoryUpdateIn(status=new_status, expected_version=data.get("version")),
        )
        applied = True

    return {
        "ok": True,
        "memory_id": memory_id,
        "applied": applied,
        "decision_id": decision_id,
        "judgment": judgment,
        "scores": scores,
    }
