# -*- coding: utf-8 -*-
"""多实例：不同 data_dir 数据隔离；同目录锁互斥。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import ObservationIn, SourceKind
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database
from mnemosyne.storage.process_lock import LockConflictError, ProcessLock


class MultiInstanceTests(unittest.TestCase):
    def test_separate_data_dirs_isolated(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            a_dir = root / "node-a" / "data"
            b_dir = root / "node-b" / "data"
            db_a = Database(a_dir / "memory.db", auto_backup_on_migrate=False)
            db_b = Database(b_dir / "memory.db", auto_backup_on_migrate=False)
            db_a.ensure_schema()
            db_b.ensure_schema()
            svc_a = MemoryService(db_a, EventBus())
            svc_b = MemoryService(db_b, EventBus())
            obs = svc_a.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="只属于节点 A 的秘密",
                    producer="a",
                )
            )
            self.assertIsNone(svc_b.get_observation(obs.id))
            self.assertIsNotNone(svc_a.get_observation(obs.id))
            # 独立锁
            la = ProcessLock.for_data_dir(root / "node-a", instance_id="a")
            lb = ProcessLock.for_data_dir(root / "node-b", instance_id="b")
            la.acquire()
            lb.acquire()
            with self.assertRaises(LockConflictError):
                ProcessLock.for_data_dir(root / "node-a", instance_id="a2").acquire()
            la.release()
            lb.release()
            db_a.close()
            db_b.close()


if __name__ == "__main__":
    unittest.main()
