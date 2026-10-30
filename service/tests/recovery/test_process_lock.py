# -*- coding: utf-8 -*-
"""同 data_dir 独占锁；异目录可并行。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.storage.process_lock import LockConflictError, ProcessLock


class ProcessLockTests(unittest.TestCase):
    def test_same_dir_second_fails(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            a = ProcessLock.for_data_dir(root, instance_id="a")
            meta = a.acquire()
            self.assertEqual(meta["instance_id"], "a")
            b = ProcessLock.for_data_dir(root, instance_id="b")
            with self.assertRaises(LockConflictError) as ctx:
                b.acquire()
            self.assertEqual(ctx.exception.code, "lock_conflict")
            a.release()
            c = ProcessLock.for_data_dir(root, instance_id="c")
            c.acquire()
            c.release()

    def test_different_dirs_parallel(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            d1 = root / "n1"
            d2 = root / "n2"
            a = ProcessLock.for_data_dir(d1, instance_id="a")
            b = ProcessLock.for_data_dir(d2, instance_id="b")
            a.acquire()
            b.acquire()
            a.release()
            b.release()


if __name__ == "__main__":
    unittest.main()
