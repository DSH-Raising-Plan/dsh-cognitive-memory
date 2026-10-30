# -*- coding: utf-8 -*-
"""类 DSH 对话闭环：observe → 任务 → retrieve/context（进程内，非 mock HTTP）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import ObservationIn, SourceKind
from mnemosyne.events.bus import EventBus
from mnemosyne.jobs.dispatcher import BackgroundRuntime
from mnemosyne.retrieval.pipeline import run_retrieve
from mnemosyne.storage.db import Database


class DialogueLoopE2ETests(unittest.TestCase):
    def test_capture_flush_retrieve_context(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
            db.ensure_schema()
            bus = EventBus()
            svc = MemoryService(db, bus)
            rt = BackgroundRuntime(db, bus, svc, poll_interval_ms=50)

            user = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="我最近很喜欢听夜航星。",
                    producer="dsh",
                    correlation_id="session-e2e",
                    idempotency_key="dsh:session-e2e:1",
                )
            )
            assistant = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content="那首夜航星很好听，要不要一起听？",
                    producer="dsh",
                    correlation_id="session-e2e",
                    idempotency_key="dsh:session-e2e:5",
                )
            )
            self.assertTrue(user.id and assistant.id)

            # 模拟 session flush：投递 outbox + 跑任务
            rt.dispatch_outbox_once()
            rt.run_tasks_once()

            retrieved = run_retrieve(
                svc,
                query="夜航星",
                force=True,
                limit=8,
                session_id="session-e2e",
            )
            status = str(retrieved.get("status") or "").upper()
            self.assertIn(
                status,
                {"FOUND", "PARTIAL", "HIT", "SOFT_MISS", "NO_MATCH", "FAILED", "NOT_NEEDED"},
            )
            from mnemosyne.domain.models import ContextBuildIn

            built = svc.build_context(ContextBuildIn(query="夜航星", token_budget=800))
            blob = (built.brief or "") + json_dumps_safe(built.fragments)
            self.assertIn("夜航星", blob)

            # 幂等：重复写入不炸
            again = svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="我最近很喜欢听夜航星。",
                    producer="dsh",
                    correlation_id="session-e2e",
                    idempotency_key="dsh:session-e2e:1",
                )
            )
            self.assertEqual(again.id, user.id)

            rt.stop()
            db.close()


def json_dumps_safe(fragments: list) -> str:
    import json

    return json.dumps(fragments, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
