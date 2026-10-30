# -*- coding: utf-8 -*-
"""迁移预检与升级前自动备份。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from mnemosyne.storage.db import Database
from mnemosyne.storage.migrate_safe import ensure_schema_safe, preflight, validate_schema


class MigrationSafetyTests(unittest.TestCase):
    def test_fresh_db_migrates_and_validates(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "memory.db"
            report = ensure_schema_safe(db_path, auto_backup=True)
            self.assertTrue(report["ok"])
            self.assertTrue(report["applied"])
            v = validate_schema(db_path)
            self.assertTrue(v["ok"])
            self.assertFalse(v["pending_migrations"])

    def test_pending_triggers_pre_migrate_backup(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            db_path = root / "data" / "memory.db"
            # 先完整迁移，再回退 002 记录以模拟待升级
            first = ensure_schema_safe(db_path, auto_backup=False)
            self.assertTrue(first["ok"])
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                "DELETE FROM schema_migrations WHERE id='002_change_plan_schema_gate'"
            )
            conn.execute("DROP TABLE IF EXISTS change_plans")
            conn.execute("DROP TABLE IF EXISTS cognitive_schemas")
            conn.execute("DROP TABLE IF EXISTS schema_versions")
            conn.execute("DROP TABLE IF EXISTS cognitive_change_plans")
            conn.execute("DROP TABLE IF EXISTS capability_permissions")
            conn.execute("DROP TABLE IF EXISTS capability_audit")
            conn.execute(
                "INSERT INTO observations(id, source_kind, content, created_at, producer, metadata_json) "
                "VALUES ('o1','dialog','hi','2020-01-01T00:00:00Z','t','{}')"
            )
            conn.commit()
            conn.close()

            pf = preflight(db_path)
            self.assertIn("002_change_plan_schema_gate", pf["pending"])
            report = ensure_schema_safe(
                db_path, auto_backup=True, backup_dir=root / "backups"
            )
            self.assertTrue(report["ok"])
            self.assertIsNotNone(report.get("backup"))
            self.assertTrue(Path(report["backup"]["bundle_dir"]).is_dir())
            v = validate_schema(db_path)
            self.assertTrue(v["ok"])

    def test_database_ensure_schema_reports(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
            applied = db.ensure_schema()
            self.assertTrue(applied)
            self.assertTrue(db.last_migrate_report and db.last_migrate_report.get("ok"))
            db.close()


if __name__ == "__main__":
    unittest.main()
