# -*- coding: utf-8 -*-
"""一致性备份 / 恢复（SQLite Backup API + integrity manifest）。"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    out: dict[str, int] = {}
    for name in names:
        try:
            out[name] = int(conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0])
        except sqlite3.Error:
            out[name] = -1
    return out


def integrity_check(db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        ok = row and str(row[0]).lower() == "ok"
        migrations = [
            r[0] for r in conn.execute("SELECT id FROM schema_migrations ORDER BY id").fetchall()
        ] if ok else []
        return {
            "ok": bool(ok),
            "integrity": str(row[0]) if row else "missing",
            "migrations": migrations,
            "counts": _table_counts(conn) if ok else {},
        }
    finally:
        conn.close()


def create_backup(
    db_path: Path,
    *,
    output_dir: Path | None = None,
    label: str = "manual",
) -> dict[str, Any]:
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"no db at {db_path}")
    out_root = Path(output_dir or (db_path.parent.parent / "backups")).resolve()
    stamp = _now_stamp()
    bundle = out_root / f"backup-{stamp}-{label}"
    bundle.mkdir(parents=True, exist_ok=True)
    dest_db = bundle / "memory.db"

    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(dest_db))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    check = integrity_check(dest_db)
    if not check["ok"]:
        raise RuntimeError(f"backup integrity failed: {check.get('integrity')}")

    checksum = _sha256_file(dest_db)
    manifest = {
        "created_at": stamp,
        "label": label,
        "source_db": str(db_path),
        "backup_db": str(dest_db),
        "bundle_dir": str(bundle),
        "schema_migrations": check["migrations"],
        "migration_version": check["migrations"][-1] if check["migrations"] else None,
        "table_counts": check["counts"],
        "integrity": check["integrity"],
        "checksum_sha256": checksum,
        "bytes": dest_db.stat().st_size,
        # 普通备份不含 runtime/token 等敏感凭据
        "excludes_secrets": True,
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def restore_backup(
    backup_path: Path,
    *,
    db_path: Path,
    force: bool = False,
) -> dict[str, Any]:
    """backup_path 可为 .db 文件、bundle 目录或 manifest.json。"""
    backup_path = Path(backup_path).resolve()
    db_path = Path(db_path).resolve()
    src_db: Path
    manifest: dict[str, Any] | None = None

    if backup_path.is_dir():
        src_db = backup_path / "memory.db"
        man = backup_path / "manifest.json"
        if man.is_file():
            manifest = json.loads(man.read_text(encoding="utf-8"))
    elif backup_path.name == "manifest.json":
        manifest = json.loads(backup_path.read_text(encoding="utf-8"))
        src_db = Path(manifest.get("backup_db") or (backup_path.parent / "memory.db"))
    else:
        src_db = backup_path
        sibling = backup_path.with_suffix(".json")
        if sibling.is_file():
            try:
                manifest = json.loads(sibling.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = None

    if not src_db.is_file():
        raise FileNotFoundError(f"backup db not found: {src_db}")

    if manifest and manifest.get("checksum_sha256"):
        actual = _sha256_file(src_db)
        if actual != manifest["checksum_sha256"]:
            raise RuntimeError(
                f"checksum mismatch: expected {manifest['checksum_sha256']}, got {actual}"
            )

    pre = integrity_check(src_db)
    if not pre["ok"]:
        raise RuntimeError(f"source backup integrity failed: {pre.get('integrity')}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    pre_restore: str | None = None
    if db_path.is_file() and not force:
        pre_restore = str(db_path.with_suffix(f".pre-restore-{_now_stamp()}.db"))
        shutil.copy2(db_path, pre_restore)

    # 用 Backup API 写入目标，避免半截文件
    src = sqlite3.connect(str(src_db))
    try:
        if db_path.is_file():
            db_path.unlink()
        dst = sqlite3.connect(str(db_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    post = integrity_check(db_path)
    if not post["ok"]:
        raise RuntimeError(f"restored db integrity failed: {post.get('integrity')}")

    return {
        "ok": True,
        "restored_to": str(db_path),
        "from": str(src_db),
        "pre_restore_copy": pre_restore,
        "migrations": post["migrations"],
        "counts": post["counts"],
    }
