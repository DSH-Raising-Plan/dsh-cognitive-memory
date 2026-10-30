# -*- coding: utf-8 -*-
"""PCIP 交换 stub：L3 默认拒绝；接收内容仅落为 Observation。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import ObservationIn, SourceKind
from mnemosyne.interop.schemas import validate_pcip_exchange
from mnemosyne.storage.db import Database
from mnemosyne.storage.ids import new_id


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def _policy_expired(policy: dict[str, Any]) -> bool:
    exp = str(policy.get("expires_at") or "").strip()
    if not exp:
        return True
    try:
        if exp.endswith("Z"):
            dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = parsedate_to_datetime(exp)
        except Exception:
            return True
    return dt <= datetime.now(timezone.utc)


def ensure_pcip_tables(db: Database) -> None:
    with db.transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pcip_exchanges (
              exchange_id TEXT PRIMARY KEY,
              level TEXT NOT NULL,
              direction TEXT NOT NULL,
              from_node TEXT NOT NULL,
              to_node TEXT NOT NULL,
              status TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )


def create_exchange_request(
    db: Database,
    request: dict[str, Any],
    *,
    local_node: str = "local",
) -> dict[str, Any]:
    ensure_pcip_tables(db)
    req = dict(request)
    req.setdefault("pcip_version", "0.1-proposal")
    req.setdefault("exchange_id", new_id("pcip"))
    req.setdefault("from_node", local_node)
    check = validate_pcip_exchange(req)
    if not check["ok"]:
        return {"ok": False, "detail": "invalid_pcip", "errors": check["errors"]}
    level = str(req.get("level") or "")
    if level == "L3":
        return {
            "ok": False,
            "detail": "l3_forbidden_by_default",
            "message": "L3 private memory exchange is denied unless explicitly unlocked later",
        }
    now = _now()
    with db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO pcip_exchanges(
              exchange_id, level, direction, from_node, to_node, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, 'outbound', ?, ?, 'proposed', ?, ?, ?)
            """,
            (
                req["exchange_id"],
                level,
                req["from_node"],
                req["to_node"],
                json.dumps(req, ensure_ascii=False),
                now,
                now,
            ),
        )
    return {"ok": True, "exchange": req, "status": "proposed"}


def accept_inbound_exchange(
    service: MemoryService,
    request: dict[str, Any],
    *,
    local_node: str = "local",
) -> dict[str, Any]:
    """接受入站交换：校验后写入 Observation（永不直接 Active Memory）。"""
    ensure_pcip_tables(service.db)
    check = validate_pcip_exchange(request)
    if not check["ok"]:
        return {"ok": False, "detail": "invalid_pcip", "errors": check["errors"]}
    if str(request.get("level")) == "L3":
        return {"ok": False, "detail": "l3_forbidden_by_default"}
    policy = dict(request.get("policy") or {})
    if policy.get("revoked"):
        return {"ok": False, "detail": "revoked"}
    if _policy_expired(policy):
        return {"ok": False, "detail": "policy_expired"}
    to_node = request.get("to_node")
    if to_node not in (local_node, "*", None):
        return {"ok": False, "detail": "to_node_mismatch"}

    preview = ((request.get("payload_ref") or {}).get("content_preview") or "").strip()
    topic = str(request.get("topic") or "")
    content = preview or f"[pcip:{request.get('level')}] topic={topic}"
    obs = service.capture_observation(
        ObservationIn(
            source_kind=SourceKind.SYSTEM,
            content=content[:4000],
            producer=f"pcip:{request.get('from_node')}",
            correlation_id=str(request.get("exchange_id")),
            metadata={
                "pcip": True,
                "level": request.get("level"),
                "policy": policy,
                "payload_ref": request.get("payload_ref"),
                "trust": "untrusted",
            },
            idempotency_key=f"pcip:{request.get('exchange_id')}",
        )
    )
    now = _now()
    with service.db.transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO pcip_exchanges(
              exchange_id, level, direction, from_node, to_node, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, 'inbound', ?, ?, 'accepted_as_observation', ?, ?, ?)
            """,
            (
                request["exchange_id"],
                request["level"],
                request["from_node"],
                request.get("to_node") or local_node,
                json.dumps({**request, "observation_id": obs.id}, ensure_ascii=False),
                now,
                now,
            ),
        )
    return {
        "ok": True,
        "status": "accepted_as_observation",
        "observation_id": obs.id,
        "note": "external content is Observation only; not Active Memory",
    }
