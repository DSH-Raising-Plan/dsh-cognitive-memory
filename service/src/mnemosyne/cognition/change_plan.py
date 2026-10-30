# -*- coding: utf-8 -*-
"""ChangePlan：变化候选 → 可审计计划；高风险需 confirm。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from mnemosyne.cognition.change_detect import detect_changes_for_observation
from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryStatus, MemoryUpdateIn

_DETECT_TO_PLAN = {
    "new": "ADD",
    "continues": "UPDATE",
    "evolves": "UPDATE",
    "corrects": "SUPERSEDE",
    "uncertain": "NO_CHANGE",
    "supersedes": "SUPERSEDE",
    "conflicts": "NO_CHANGE",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _risk_and_approval(change_type: str, confidence: float) -> tuple[str, str]:
    if change_type in ("NO_CHANGE",) or confidence < 0.45:
        return "high", "human"
    if change_type in ("SUPERSEDE", "INVALIDATE", "MERGE") or confidence < 0.7:
        return "medium", "human"
    if change_type == "ADD" and confidence >= 0.7:
        return "low", "auto_ok"
    return "medium", "human"


def candidate_to_plan_payload(observation_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    raw = str(candidate.get("change_type") or "uncertain")
    plan_type = _DETECT_TO_PLAN.get(raw, "NO_CHANGE")
    if raw == "corrects" and float(candidate.get("confidence") or 0) >= 0.75:
        plan_type = "INVALIDATE"
    conf = float(candidate.get("confidence") or 0.0)
    risk, approval = _risk_and_approval(plan_type, conf)
    targets = [str(candidate["memory_id"])] if candidate.get("memory_id") else []
    return {
        "change_id": f"cpl_{uuid.uuid4().hex[:16]}",
        "observation_id": observation_id,
        "target_memory_ids": targets,
        "change_type": plan_type,
        "detect_change_type": raw,
        "evidence_refs": [observation_id],
        "reason": str(candidate.get("reason") or ""),
        "risk_level": risk,
        "confidence": conf,
        "approval_requirement": approval,
        "expected_changes": {
            "relation": candidate.get("suggested_relation"),
            "similarity": candidate.get("similarity"),
            "preview": candidate.get("memory_content_preview"),
        },
        "execution_status": "proposed",
        "verification_status": "pending",
        "rollback_reference": None,
        "source_candidate": candidate,
    }


def build_plans_for_observation(
    service: MemoryService,
    observation_id: str,
    *,
    dry_run: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    detected = detect_changes_for_observation(service, observation_id, dry_run=True)
    if not detected.get("ok"):
        return {"ok": False, "detail": detected.get("detail"), "plans": []}
    plans = [
        candidate_to_plan_payload(observation_id, c)
        for c in (detected.get("candidates") or [])
    ]
    if persist:
        for p in plans:
            service.store_change_plan(p)
    return {
        "ok": True,
        "observation_id": observation_id,
        "dry_run": dry_run,
        "plans": plans,
        "count": len(plans),
    }


def apply_change_plan(
    service: MemoryService,
    plan_id: str,
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    plan = service.get_change_plan(plan_id)
    if not plan:
        return {"ok": False, "detail": "plan_not_found"}
    if str(plan.get("execution_status")) == "applied":
        return {"ok": False, "detail": "already_applied"}
    risk = str(plan.get("risk_level") or "medium").lower()
    approval = str(plan.get("approval_requirement") or "human")
    if (risk in ("medium", "high") or approval == "human") and not confirm:
        return {"ok": False, "detail": "confirm_required", "risk_level": risk}

    ctype = str(plan.get("change_type") or "NO_CHANGE")
    targets = list(plan.get("target_memory_ids") or [])
    snapshots: list[dict[str, Any]] = []
    for mid in targets:
        cur = service.get_memory(mid)
        snapshots.append({"memory_id": mid, "before": cur})
        if ctype == "INVALIDATE":
            service.update_memory(mid, MemoryUpdateIn(status=MemoryStatus.INVALIDATED))
        elif ctype == "SUPERSEDE":
            service.update_memory(mid, MemoryUpdateIn(status=MemoryStatus.SUPERSEDED))

    rb = f"rb_{uuid.uuid4().hex[:12]}"
    service.update_change_plan(
        plan_id,
        execution_status="applied",
        verification_status="applied",
        rollback_reference=rb,
        payload_patch={"rollback_snapshots": snapshots, "confirm": confirm},
    )
    return {"ok": True, "plan_id": plan_id, "change_type": ctype, "rollback_reference": rb}


def rollback_change_plan(service: MemoryService, plan_id: str) -> dict[str, Any]:
    plan = service.get_change_plan(plan_id)
    if not plan:
        return {"ok": False, "detail": "plan_not_found"}
    snaps = list((plan.get("rollback_snapshots") or []))
    restored = []
    for snap in snaps:
        mid = snap.get("memory_id")
        before = snap.get("before") or {}
        if not mid or not before:
            continue
        st = before.get("status")
        if st:
            service.update_memory(mid, MemoryUpdateIn(status=MemoryStatus(st)))
            restored.append(mid)
    service.update_change_plan(
        plan_id,
        execution_status="rolled_back",
        verification_status="rolled_back",
        payload_patch={"rolled_back_at": _now(), "restored": restored},
    )
    return {"ok": True, "plan_id": plan_id, "restored": restored}
