# -*- coding: utf-8 -*-
"""备份 / 恢复 round-trip（含 WAL、关联与任务）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SourceKind,
    TaskCreateIn,
)
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.backup import create_backup, integrity_check, restore_backup
from mnemosyne.storage.db import Database


class BackupRoundtripTests(unittest.TestCase):
    def test_roundtrip_preserves_graph(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            db_path = root / "data" / "memory.db"
            db = Database(db_path, auto_backup_on_migrate=False)
            db.ensure_schema()
            svc = MemoryService(db, EventBus())
            obs = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="主人喜欢抹茶拿铁",
                    producer="test",
                )
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.CANDIDATE,
                    content="喜欢抹茶",
                    source_ids=[obs.id],
                )
            )
            mem2 = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.CANDIDATE,
                    content="喜欢拿铁",
                    source_ids=[obs.id],
                )
            )
            svc.link_memories(from_id=mem.id, to_id=mem2.id, relation="derives", note="test")
            svc.create_task(TaskCreateIn(task_type="memory.promote_check", payload={"memory_id": mem.id}))
            # 触发 WAL
            db.connect().execute("PRAGMA wal_checkpoint(FULL)")
            db.close()

            bak = create_backup(db_path, output_dir=root / "backups", label="rt")
            self.assertTrue(bak["checksum_sha256"])
            self.assertGreater(bak["table_counts"].get("observations", 0), 0)

            # 破坏数据
            db2 = Database(db_path, auto_backup_on_migrate=False)
            db2.ensure_schema()
            svc2 = MemoryService(db2, EventBus())
            svc2.forget_memory(mem.id, hard=True)
            db2.close()

            restore_backup(Path(bak["bundle_dir"]), db_path=db_path, force=True)
            check = integrity_check(db_path)
            self.assertTrue(check["ok"])

            db3 = Database(db_path, auto_backup_on_migrate=False)
            db3.ensure_schema()
            svc3 = MemoryService(db3, EventBus())
            got = svc3.get_memory(mem.id, include_evidence=True)
            self.assertEqual(got["content"], "喜欢抹茶")
            self.assertGreaterEqual(len(got.get("evidence") or []), 1)
            rels = svc3.list_relations(mem.id)
            self.assertGreaterEqual(len(rels), 1)
            tasks = db3.connect().execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE status='pending'"
            ).fetchone()["n"]
            self.assertGreaterEqual(tasks, 1)
            db3.close()


if __name__ == "__main__":
    unittest.main()
