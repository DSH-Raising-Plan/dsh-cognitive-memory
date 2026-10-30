# -*- coding: utf-8 -*-
"""Evidence 创建 / 查询与 Observation 状态。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.cognition.consolidate import consolidate_observation
from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import (
    EvidenceIn,
    ObservationIn,
    ObservationStatus,
    RelationKind,
    SourceKind,
)
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database


class EvidenceApiTests(unittest.TestCase):
    def test_add_list_and_observation_processed(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
            db.ensure_schema()
            svc = MemoryService(db, EventBus())
            obs = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content="今天看了星际穿越",
                    producer="test",
                )
            )
            self.assertEqual(obs.status, ObservationStatus.OBSERVED)
            mid = consolidate_observation(svc, obs.id)
            self.assertTrue(mid)
            got = svc.get_observation(obs.id)
            self.assertEqual(got["status"], ObservationStatus.PROCESSED.value)
            items = svc.list_evidence(subject_id=mid)
            self.assertGreaterEqual(len(items), 1)
            svc.add_evidence(
                EvidenceIn(
                    subject_id=mid,
                    source_id=obs.id,
                    evidence_type=RelationKind.DERIVES,
                    content_ref="note",
                )
            )
            # DERIVES 与 supports 不同 unique 键
            items2 = svc.list_evidence(subject_id=mid)
            self.assertGreaterEqual(len(items2), 2)
            db.close()


if __name__ == "__main__":
    unittest.main()
