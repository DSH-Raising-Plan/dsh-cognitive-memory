# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryStatus, SearchQuery
from mnemosyne.events.bus import EventBus
from mnemosyne.federation.pcip import accept_inbound_exchange, create_exchange_request
from mnemosyne.storage.db import Database


class PcipFederationTests(unittest.TestCase):
    def test_l3_denied_and_inbound_becomes_observation_only(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = Database(Path(tmp) / "memory.db", auto_backup_on_migrate=False)
            db.ensure_schema()
            svc = MemoryService(db, EventBus())
            denied = create_exchange_request(
                db,
                {
                    "level": "L3",
                    "to_node": "peer",
                    "topic": "private",
                    "policy": {
                        "allow_store": False,
                        "allow_forward": False,
                        "allow_train": False,
                        "expires_at": "2099-01-01T00:00:00Z",
                    },
                    "payload_ref": {"kind": "memory", "udm_id": "m1"},
                },
            )
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["detail"], "l3_forbidden_by_default")

            accepted = accept_inbound_exchange(
                svc,
                {
                    "pcip_version": "0.1-proposal",
                    "exchange_id": "pcip_in_1",
                    "level": "L1",
                    "from_node": "peer-a",
                    "to_node": "local",
                    "topic": "music",
                    "policy": {
                        "allow_store": True,
                        "allow_forward": False,
                        "allow_train": False,
                        "expires_at": "2099-01-01T00:00:00Z",
                    },
                    "payload_ref": {
                        "kind": "observation",
                        "udm_id": "ext_1",
                        "content_preview": "peer says likes jazz",
                    },
                },
            )
            self.assertTrue(accepted["ok"])
            oid = accepted["observation_id"]
            obs = svc.get_observation(oid)
            self.assertIsNotNone(obs)
            self.assertTrue((obs or {}).get("metadata", {}).get("pcip"))
            # 不应自动变成 ACTIVE semantic memory
            actives = svc.search(
                SearchQuery(query="jazz", status=[MemoryStatus.ACTIVE], limit=20)
            )
            # working memory from dialog-like may exist but content is system obs —
            # ensure no auto ACTIVE semantic from peer fact
            semantic_active = [
                m for m in actives if m.type.value == "semantic" and "jazz" in m.content
            ]
            self.assertEqual(semantic_active, [])
            db.close()


if __name__ == "__main__":
    unittest.main()
