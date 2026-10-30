# -*- coding: utf-8 -*-
"""组件身份与 scope 拒绝。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from mnemosyne.bootstrap import build_context
from mnemosyne.governance.component_auth import register_component


class ComponentAuthTests(unittest.TestCase):
    def test_insufficient_scope_forbidden(self) -> None:
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
            # 强制组件；只读组件不能 POST observations
            app = __import__("mnemosyne.api.app", fromlist=["create_app"]).create_app(
                ctx.service, access_token="tok", require_component=True
            )
            register_component(
                ctx.db,
                component_id="readonly.bot",
                name="Readonly",
                scopes=["memory.read", "memory.search"],
            )
            client = TestClient(app)
            denied = client.post(
                "/api/v1/observations",
                headers={
                    "Authorization": "Bearer tok",
                    "X-Component-Id": "readonly.bot",
                },
                json={
                    "source_kind": "dialog",
                    "content": "should fail",
                    "producer": "test",
                },
            )
            self.assertEqual(denied.status_code, 403)
            allowed = client.post(
                "/api/v1/memories/search",
                headers={
                    "Authorization": "Bearer tok",
                    "X-Component-Id": "readonly.bot",
                },
                json={"query": "x", "limit": 3},
            )
            self.assertEqual(allowed.status_code, 200)
            ctx.db.close()

    def test_legacy_without_component_still_works(self) -> None:
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
            res = client.post(
                "/api/v1/observations",
                headers={"Authorization": "Bearer tok"},
                json={"source_kind": "dialog", "content": "legacy ok", "producer": "t"},
            )
            self.assertEqual(res.status_code, 200)
            ctx.db.close()


if __name__ == "__main__":
    unittest.main()
