# -*- coding: utf-8 -*-
"""迁移预检 / 升级前备份 / 迁移后校验。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mnemosyne.storage.backup import create_backup, integrity_check
from mnemosyne.storage.migrations import MIGRATIONS, apply_migrations


EXPECTED_CORE_TABLES = {
    "schema_migrations",
    "observations",
    "memories",
    "memory_evidence",
    "memory_relations",
    "events",
    "outbox",
    "inbox",
    "tasks",
    "evidences",
    "decision_logs",
}


def pending_migrations(conn: sqlite3.Connection) -> list[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )
    applied = {row[0] for row in conn.execute("SELECT id FROM schema_migrations").fetchall()}
    return [mid for mid, _ in MIGRATIONS if mid not in applied]


def preflight(db_path: Path) -> dict[str, Any]:
    db_path = Path(db_path).resolve()
    exists = db_path.is_file()
    result: dict[str, Any] = {
        "ok": True,
        "db_path": str(db_path),
        "db_exists": exists,
        "pending": [],
        "integrity": None,
        "warnings": [],
    }
    if not exists:
        result["pending"] = [mid for mid, _ in MIGRATIONS]
        return result
    check = integrity_check(db_path)
    result["integrity"] = check
    if not check["ok"]:
        result["ok"] = False
        result["warnings"].append("integrity_check_failed")
        return result
    conn = sqlite3.connect(str(db_path))
    try:
        result["pending"] = pending_migrations(conn)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = sorted(EXPECTED_CORE_TABLES - tables)
        # 空库或仅有 migrations 表时，pending 会补齐
        if missing and not result["pending"]:
            result["warnings"].append(f"missing_tables:{','.join(missing)}")
    finally:
        conn.close()
    return result


def validate_schema(db_path: Path) -> dict[str, Any]:
    check = integrity_check(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = sorted(EXPECTED_CORE_TABLES - tables)
        pending = pending_migrations(conn)
    finally:
        conn.close()
    ok = bool(check["ok"]) and not missing and not pending
    return {
        "ok": ok,
        "integrity": check,
        "missing_tables": missing,
        "pending_migrations": pending,
    }


def ensure_schema_safe(
    db_path: Path,
    *,
    auto_backup: bool = True,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    """升级前预检与可选自动备份，再 apply_migrations，最后校验。"""
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    pf = preflight(db_path)
    if not pf["ok"]:
        return {"ok": False, "phase": "preflight", "preflight": pf}

    backup_meta = None
    pending = list(pf.get("pending") or [])
    if pending and auto_backup and db_path.is_file() and db_path.stat().st_size > 0:
        # 仅当已有数据且有待迁移时备份
        out = backup_dir or (db_path.parent.parent / "backups")
        backup_meta = create_backup(db_path, output_dir=out, label="pre-migrate")

    conn = sqlite3.connect(str(db_path))
    try:
        applied = apply_migrations(conn)
    finally:
        conn.close()

    validation = validate_schema(db_path)
    return {
        "ok": bool(validation["ok"]),
        "phase": "done",
        "preflight": pf,
        "applied": applied,
        "backup": backup_meta,
        "validation": validation,
    }
