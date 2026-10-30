# -*- coding: utf-8 -*-
"""promote_v2：独立性、反证、Decision Log。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.cognition.promote import evaluate_and_apply
from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import (
    EvidenceIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    RelationKind,
    SourceKind,
)
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database


class PromoteV2Tests(unittest.TestCase):
    def _svc(self, tmp: str) -> MemoryService:
        db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
        db.ensure_schema()
        return MemoryService(db, EventBus())

    def test_duplicate_sources_not_enough(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc = self._svc(tmp)
            # 同一 correlation → 不独立
            o1 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content="喜欢抹茶A",
                    producer="dsh",
                    correlation_id="sess-1",
                )
            )
            o2 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content="喜欢抹茶B",
                    producer="dsh",
                    correlation_id="sess-1",
                )
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    content="喜欢抹茶",
                    source_ids=[o1.id, o2.id],
                    status=MemoryStatus.CANDIDATE,
                )
            )
            result = evaluate_and_apply(svc, mem.id)
            self.assertTrue(result["ok"])
            self.assertFalse(result["applied"])
            self.assertEqual(result["judgment"]["decision"], "hold")
            self.assertIn("independent", result["judgment"]["reason"])
            got = svc.get_memory(mem.id)
            self.assertEqual(got["status"], MemoryStatus.CANDIDATE.value)
            logs = svc.list_decision_logs(subject_id=mem.id)
            self.assertGreaterEqual(len(logs), 1)

    def test_two_independent_sources_promote(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc = self._svc(tmp)
            o1 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="我喜欢抹茶",
                    producer="dsh",
                    correlation_id="day-1",
                )
            )
            o2 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="还是喜欢抹茶",
                    producer="dsh",
                    correlation_id="day-2",
                )
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    content="喜欢抹茶",
                    source_ids=[o1.id, o2.id],
                    status=MemoryStatus.CANDIDATE,
                )
            )
            result = evaluate_and_apply(svc, mem.id)
            self.assertTrue(result["applied"])
            self.assertEqual(result["judgment"]["outcome"], "active")
            self.assertEqual(svc.get_memory(mem.id)["status"], MemoryStatus.ACTIVE.value)

    def test_counter_evidence_needs_review(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            svc = self._svc(tmp)
            o1 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="喜欢抹茶",
                    producer="dsh",
                    correlation_id="a",
                )
            )
            o2 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="确认喜欢抹茶",
                    producer="dsh",
                    correlation_id="b",
                )
            )
            o3 = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="不喜欢抹茶了",
                    producer="dsh",
                    correlation_id="c",
                )
            )
            mem = svc.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    content="喜欢抹茶",
                    source_ids=[o1.id, o2.id],
                    status=MemoryStatus.CANDIDATE,
                )
            )
            svc.add_evidence(
                EvidenceIn(
                    subject_id=mem.id,
                    source_id=o3.id,
                    evidence_type=RelationKind.CONTRADICTS,
                    provenance={"correlation_id": "c", "producer": "dsh"},
                )
            )
            result = evaluate_and_apply(svc, mem.id)
            self.assertTrue(result["applied"])
            self.assertEqual(result["judgment"]["outcome"], "needs_review")
            self.assertEqual(
                svc.get_memory(mem.id)["status"], MemoryStatus.NEEDS_REVIEW.value
            )


if __name__ == "__main__":
    unittest.main()
