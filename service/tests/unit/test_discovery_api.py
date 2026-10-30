# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from mnemosyne.bootstrap import build_context


class DiscoveryApiTests(unittest.TestCase):
    def test_discovery_lists_pcip_and_schemas(self) -> None:
        try:
            import httpx  # noqa: F401
        except ImportError:
            self.skipTest("httpx not installed")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ctx = build_context(
                data_dir=tmp,
                token="tok",
                acquire_lock=False,
                auto_backup_on_migrate=False,
            )
            client = TestClient(ctx.app)
            r = client.get(
                "/api/v1/discovery",
                headers={"Authorization": "Bearer tok"},
            )
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertTrue(body.get("ok"))
            self.assertEqual(body.get("baseline"), "foundation-0.1.0")
            self.assertIn("pcip", body)
            self.assertEqual(body["pcip"].get("l3_default"), "forbidden")
            self.assertEqual(body["pcip"].get("inbound_trust_default"), "untrusted")
            self.assertTrue(any("component-contract" in s for s in body.get("schemas") or []))
            ctx.db.close()


if __name__ == "__main__":
    unittest.main()
