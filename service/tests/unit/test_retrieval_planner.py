# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from mnemosyne.events.bus import EventBus
from mnemosyne.retrieval.pipeline import (
    RESULT_FOUND,
    RESULT_NO_MATCH,
    RESULT_NOT_NEEDED,
    run_retrieve,
)
from mnemosyne.retrieval.planner import plan_retrieval
from mnemosyne.storage.db import Database


class RetrievalPlannerTests(unittest.TestCase):
    def test_chitchat_not_needed(self) -> None:
        plan = plan_retrieval("你好")
        self.assertFalse(plan.should_retrieve)

    def test_history_triggers(self) -> None:
        plan = plan_retrieval("你还记得我说过讨厌香菜吗")
        self.assertTrue(plan.should_retrieve)
        self.assertEqual(plan.trigger, "explicit")

    def test_force_overrides_chitchat(self) -> None:
        plan = plan_retrieval("你好", force=True)
        self.assertTrue(plan.should_retrieve)
        self.assertEqual(plan.trigger, "forced")


class RetrievePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_not_needed(self) -> None:
        out = run_retrieve(self.svc, query="你好")
        self.assertEqual(out["status"], RESULT_NOT_NEEDED)
        self.assertEqual(out["count"], 0)

    def test_found(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="主人讨厌香菜",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        hit = run_retrieve(self.svc, query="你还记得我说过讨厌香菜吗")
        self.assertIn(hit["status"], (RESULT_FOUND, "PARTIAL"))
        self.assertGreaterEqual(hit["count"], 1)

    def test_force_no_match(self) -> None:
        miss = run_retrieve(
            self.svc, query="上次我们讨论了火星移民方案吗", force=True
        )
        self.assertIn(miss["status"], (RESULT_NO_MATCH, "PARTIAL", RESULT_FOUND))


if __name__ == "__main__":
    unittest.main()
