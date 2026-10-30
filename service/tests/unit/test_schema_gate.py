# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.cognition.schema_discovery import discover_schema_candidates
from mnemosyne.cognition.schema_ops import assimilate_schema, accommodate_schema
from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from mnemosyne.events.bus import EventBus
from mnemosyne.governance.capability_gate import (
    CapabilityLockedError,
    check_capability,
    ensure_default_capabilities,
    list_capabilities,
    require_capability,
)
from mnemosyne.governance.reinforcement_learning import run_offline_training
from mnemosyne.storage.db import Database


class SchemaGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        ensure_default_capabilities(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_gate_locked(self) -> None:
        caps = list_capabilities(self.db)
        self.assertGreaterEqual(len(caps), 6)
        self.assertFalse(check_capability(self.db, "RL_OFFLINE_TRAINING")["allowed"])
        with self.assertRaises(CapabilityLockedError):
            require_capability(self.db, "RL_POLICY_DEPLOYMENT")
        self.assertEqual(run_offline_training(self.db, {}).get("detail"), "capability_locked")

    def test_schema_roundtrip(self) -> None:
        sid = self.svc.store_cognitive_schema(
            {
                "name": "模式·测试",
                "description": "候选",
                "type": "CONTEXTUAL",
                "state": "PROPOSED",
                "evidence": {"supporting": [], "counter": []},
                "applicability": {"scope": [], "exclusions": []},
            }
        )
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人忙碌时喜欢简洁回复",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        a = assimilate_schema(self.svc, sid, memory_ids=[mem.id])
        self.assertTrue(a["ok"])
        b = accommodate_schema(self.svc, sid, memory_ids=[mem.id], counter_note="例外")
        self.assertTrue(b["ok"])

    def test_discover(self) -> None:
        for i in range(4):
            self.svc.propose_memory(
                MemoryProposeIn(
                    content=f"主人喜欢听夜航星 重复主题 夜航星{i}",
                    type=MemoryType.EPISODIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
        pack = discover_schema_candidates(
            self.svc, limit_memories=50, min_cluster=3, min_similarity=0.15, persist=True
        )
        self.assertTrue(pack.get("ok"))


if __name__ == "__main__":
    unittest.main()
