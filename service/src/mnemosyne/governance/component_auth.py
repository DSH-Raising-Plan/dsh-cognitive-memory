# -*- coding: utf-8 -*-
"""组件身份 + 能力范围（在 Bearer Token 之上；注册 ≠ 随意扩权）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mnemosyne.storage.db import Database
from mnemosyne.storage.ids import new_id

ALL_SCOPES = [
    "identity.read",
    "observation.create",
    "observation.read",
    "observation.delete",
    "memory.read",
    "memory.search",
    "memory.create",
    "memory.update",
    "memory.delete",
    "evidence.read",
    "evidence.create",
    "context.build",
    "relationship.read",
    "relationship.create",
    "event.publish",
    "event.subscribe",
    "exchange.request",
    "exchange.accept",
]

DEFAULT_COMPONENTS = {
    "dsh.host": {
        "name": "DSH Host Adapter",
        "scopes": list(ALL_SCOPES),
    },
    "mcp.client": {
        "name": "MCP Client",
        "scopes": [
            "memory.read",
            "memory.search",
            "memory.create",
            "memory.update",
            "memory.delete",
            "observation.create",
            "observation.read",
            "evidence.read",
            "evidence.create",
            "context.build",
        ],
    },
    "cli.local": {
        "name": "Local CLI",
        "scopes": list(ALL_SCOPES),
    },
}

# 路由前缀 → 所需 scope（取一即可匹配）
ROUTE_SCOPES: list[tuple[str, str, list[str]]] = [
    ("POST", "/api/v1/observations", ["observation.create"]),
    ("GET", "/api/v1/observations/", ["observation.read"]),
    ("DELETE", "/api/v1/observations/", ["observation.delete"]),
    ("POST", "/api/v1/memories/search", ["memory.search", "memory.read"]),
    ("GET", "/api/v1/memories/", ["memory.read"]),
    ("POST", "/api/v1/memories", ["memory.create"]),
    ("PATCH", "/api/v1/memories/", ["memory.update"]),
    ("DELETE", "/api/v1/memories/", ["memory.delete"]),
    ("POST", "/api/v1/memories/", ["memory.update", "memory.delete", "memory.read"]),
    ("POST", "/api/v1/contexts/build", ["context.build"]),
    ("POST", "/api/v1/retrieve", ["memory.search", "context.build"]),
    ("POST", "/api/v1/evidences", ["evidence.create"]),
    ("GET", "/api/v1/memories/", ["evidence.read", "memory.read"]),
    ("POST", "/api/v1/relations", ["relationship.create"]),
    ("GET", "/api/v1/health", ["identity.read", "memory.read"]),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_default_components(db: Database) -> None:
    conn = db.connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS components (
              component_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              scopes_json TEXT NOT NULL DEFAULT '[]',
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS component_audit (
              id TEXT PRIMARY KEY,
              component_id TEXT NOT NULL,
              action TEXT NOT NULL,
              path TEXT NOT NULL DEFAULT '',
              detail_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL
            )
            """
        )
        now = _now()
        for cid, meta in DEFAULT_COMPONENTS.items():
            exists = conn.execute(
                "SELECT 1 FROM components WHERE component_id=?", (cid,)
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO components(component_id, name, scopes_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (cid, meta["name"], json.dumps(meta["scopes"], ensure_ascii=False), now, now),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_component(db: Database, component_id: str) -> dict[str, Any] | None:
    row = db.connect().execute(
        "SELECT * FROM components WHERE component_id=?", (component_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "component_id": row["component_id"],
        "name": row["name"],
        "scopes": json.loads(row["scopes_json"] or "[]"),
        "enabled": bool(row["enabled"]),
    }


def register_component(
    db: Database,
    *,
    component_id: str,
    name: str,
    scopes: list[str],
) -> dict[str, Any]:
    now = _now()
    with db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO components(component_id, name, scopes_json, enabled, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(component_id) DO UPDATE SET
              name=excluded.name,
              scopes_json=excluded.scopes_json,
              updated_at=excluded.updated_at
            """,
            (component_id, name, json.dumps(scopes, ensure_ascii=False), now, now),
        )
    return get_component(db, component_id) or {}


def required_scopes_for(method: str, path: str) -> list[str]:
    method = method.upper()
    for m, prefix, scopes in ROUTE_SCOPES:
        if method == m and (path == prefix or path.startswith(prefix)):
            return scopes
    return []


def check_component_access(
    db: Database,
    *,
    component_id: str | None,
    method: str,
    path: str,
    require_component: bool = False,
) -> dict[str, Any]:
    """返回 {allowed, detail, component}。无 component 且不强制时放行（本地 MVP 兼容）。"""
    needed = required_scopes_for(method, path)
    if not component_id:
        if require_component:
            return {"allowed": False, "detail": "component_required", "needed": needed}
        return {"allowed": True, "detail": "legacy_token_only", "needed": needed, "component": None}

    comp = get_component(db, component_id)
    if not comp or not comp.get("enabled"):
        return {"allowed": False, "detail": "component_unknown_or_disabled", "needed": needed}
    if not needed:
        return {"allowed": True, "detail": "no_scope_mapped", "component": comp, "needed": []}
    have = set(comp.get("scopes") or [])
    if have.intersection(needed) or "*" in have:
        _audit(db, component_id, "allow", path, {"needed": needed})
        return {"allowed": True, "detail": "ok", "component": comp, "needed": needed}
    _audit(db, component_id, "deny", path, {"needed": needed, "have": sorted(have)})
    return {
        "allowed": False,
        "detail": "insufficient_scope",
        "needed": needed,
        "have": sorted(have),
        "component": comp,
    }


def _audit(db: Database, component_id: str, action: str, path: str, detail: dict[str, Any]) -> None:
    try:
        with db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO component_audit(id, component_id, action, path, detail_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("ca"),
                    component_id,
                    action,
                    path,
                    json.dumps(detail, ensure_ascii=False),
                    _now(),
                ),
            )
    except Exception:
        pass
