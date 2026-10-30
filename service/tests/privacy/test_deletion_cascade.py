# -*- coding: utf-8 -*-
"""Observation 删除与 Hard Forget 级联。"""

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
from mnemosyne.jobs.dispatcher import BackgroundRuntime
from mnemosyne.storage.db import Database


class DeletionCascadeTests(unittest.TestCase):
    def _svc(self, tmp: str) -> tuple[MemoryService, Database]:
        db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
        db.ensure_schema()
        return MemoryService(db, EventBus()), db

    def test_hard_forget_clears_versions_relations_schema(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc, db = self._svc(tmp)
            obs = svc.capture_observation(
                ObservationIn(source_kind=SourceKind.DIALOG, content="秘密：银行卡号123", producer="t")
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    content="银行卡号123",
                    source_ids=[obs.id],
                    status=MemoryStatus.CANDIDATE,
                )
            )
            mem2 = svc.propose_memory(
                MemoryProposeIn(type=MemoryType.SEMANTIC, content="相关", status=MemoryStatus.CANDIDATE)
            )
            svc.link_memories(from_id=mem.id, to_id=mem2.id, relation="derives")
            sid = svc.store_cognitive_schema(
                {
                    "name": "finance",
                    "state": "PROPOSED",
                    "evidence": {"supporting": [mem.id]},
                }
            )
            svc.create_task(
                TaskCreateIn(task_type="memory.promote_check", payload={"memory_id": mem.id})
            )
            out = svc.forget_memory(mem.id, hard=True)
            self.assertTrue(out["deleted"])
            conn = db.connect()
            self.assertIsNone(
                conn.execute("SELECT 1 FROM memories WHERE id=?", (mem.id,)).fetchone()
            )
            self.assertIsNone(
                conn.execute(
                    "SELECT 1 FROM memory_versions WHERE memory_id=?", (mem.id,)
                ).fetchone()
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM memory_relations WHERE from_id=? OR to_id=?",
                    (mem.id, mem.id),
                ).fetchone()["n"],
                0,
            )
            sch = svc.get_cognitive_schema(sid)
            supporting = (sch or {}).get("evidence", {}).get("supporting") or []
            self.assertNotIn(mem.id, supporting)
            pending = conn.execute(
                "SELECT status FROM tasks WHERE payload_json LIKE ?",
                (f"%{mem.id}%",),
            ).fetchall()
            self.assertTrue(all(r["status"] == "cancelled" for r in pending))
            db.close()

    def test_observation_delete_cascades_unique_memory(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc, db = self._svc(tmp)
            obs = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="只在这里出现的隐私句",
                    producer="t",
                )
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.EPISODIC,
                    content="隐私句摘要",
                    source_ids=[obs.id],
                    status=MemoryStatus.CANDIDATE,
                )
            )
            plan = svc.build_deletion_plan(observation_id=obs.id, hard=True)
            self.assertIn(mem.id, plan["memories"])
            result = svc.delete_observation(obs.id, hard=True, cascade_memories=True)
            self.assertTrue(result["deleted"])
            self.assertTrue(any(f["id"] == mem.id for f in result["forgotten_memories"]))
            conn = db.connect()
            self.assertIsNone(
                conn.execute("SELECT 1 FROM observations WHERE id=?", (obs.id,)).fetchone()
            )
            self.assertIsNone(
                conn.execute("SELECT 1 FROM memories WHERE id=?", (mem.id,)).fetchone()
            )
            db.close()

    def test_deleted_resource_tasks_do_not_revive(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc, db = self._svc(tmp)
            obs = svc.capture_observation(
                ObservationIn(source_kind=SourceKind.DIALOG, content="将被删除", producer="t")
            )
            # capture 已入队 consolidation
            svc.delete_observation(obs.id, hard=True, cascade_memories=True)
            rt = BackgroundRuntime(db, EventBus(), svc, poll_interval_ms=50)
            rt.run_tasks_once()
            # 不应再创建以该 observation 为证据的 episodic
            n = db.connect().execute(
                """
                SELECT COUNT(*) AS n FROM memories m
                JOIN memory_evidence e ON e.memory_id=m.id
                WHERE e.observation_id=?
                """,
                (obs.id,),
            ).fetchone()["n"]
            self.assertEqual(n, 0)
            rt.stop()
            db.close()


if __name__ == "__main__":
    unittest.main()
