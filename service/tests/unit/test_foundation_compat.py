# -*- coding: utf-8 -*-
"""P3.1-C: Foundation compatibility — register, unknown fields, version mismatch."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from mnemosyne.bootstrap import build_context
from mnemosyne.interop.schemas import validate_pcip_exchange, validate_udm
from mnemosyne.interop.versions import load_version_baseline


class FoundationCompatTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            import httpx  # noqa: F401
        except ImportError:
            self.skipTest("httpx not installed")
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(
            data_dir=self.tmp.name,
            token="tok",
            acquire_lock=False,
            auto_backup_on_migrate=False,
        )
        self.client = TestClient(self.ctx.app)
        self.h = {"Authorization": "Bearer tok"}

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_version_baseline_file(self) -> None:
        b = load_version_baseline()
        self.assertEqual(b["baseline"], "foundation-0.1.0")
        self.assertEqual(b["api"]["mnemosyne_api"], "v1")
        self.assertEqual(b["pcip"]["pcip_version"], "0.1-proposal")

    def test_discovery_exposes_baseline(self) -> None:
        r = self.client.get("/api/v1/discovery", headers=self.h)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("baseline"), "foundation-0.1.0")
        self.assertEqual(body["pcip"]["l3_default"], "forbidden")
        self.assertIn("versions", body)

    def test_reregister_updates_scopes_consistently(self) -> None:
        contract = {
            "component_id": "example.compat.adapter",
            "name": "Compat",
            "version": "1.0.0",
            "type": "adapter",
            "interfaces": [{"name": "identity.read", "version": "1.0"}],
            "protocols": ["rest"],
            "capabilities": ["identity.read"],
            "compatibility": {"mnemosyne_api": "^1.0"},
        }
        r1 = self.client.post(
            "/api/v1/components/register",
            headers=self.h,
            json={**contract, "scopes": ["identity.read"]},
        )
        self.assertEqual(r1.status_code, 200, r1.text)
        contract2 = {
            **contract,
            "capabilities": ["identity.read", "memory.read"],
            "scopes": ["identity.read", "memory.read", "*"],
        }
        r2 = self.client.post(
            "/api/v1/components/register",
            headers={**self.h, "X-Component-Id": "example.compat.adapter"},
            json=contract2,
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        scopes = r2.json()["component"]["scopes"]
        self.assertIn("identity.read", scopes)
        self.assertIn("memory.read", scopes)
        self.assertNotIn("*", scopes)

    def test_unknown_contract_field_rejected(self) -> None:
        bad = {
            "component_id": "example.bad",
            "name": "Bad",
            "version": "1.0.0",
            "type": "adapter",
            "interfaces": [{"name": "x", "version": "1"}],
            "protocols": ["rest"],
            "capabilities": ["identity.read"],
            "compatibility": {"mnemosyne_api": "^1.0"},
            "not_a_real_field": True,
        }
        r = self.client.post(
            "/api/v1/components/register", headers=self.h, json=bad
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"]["code"], "invalid_contract")

    def test_pcip_version_mismatch(self) -> None:
        doc = {
            "pcip_version": "9.9",
            "exchange_id": "x",
            "level": "L1",
            "from_node": "a",
            "to_node": "local",
            "topic": "t",
            "policy": {
                "allow_store": True,
                "allow_forward": False,
                "allow_train": False,
                "expires_at": "2099-01-01T00:00:00Z",
            },
            "payload_ref": {"kind": "observation", "udm_id": "u1"},
        }
        self.assertFalse(validate_pcip_exchange(doc)["ok"])

    def test_udm_version_mismatch(self) -> None:
        doc = {
            "udm_version": "2.0",
            "kind": "observation",
            "id": "o1",
            "recorded_at": "2026-01-01T00:00:00Z",
            "canonical": {"content": "x"},
            "provenance": {"producer": "t", "source_node": "local"},
        }
        self.assertFalse(validate_udm(doc)["ok"])

    def test_unauthorized_discovery(self) -> None:
        r = self.client.get("/api/v1/discovery")
        self.assertEqual(r.status_code, 401)

    def test_insufficient_scope_on_pcip(self) -> None:
        self.client.post(
            "/api/v1/components/register",
            headers=self.h,
            json={
                "component_id": "example.readonly",
                "name": "RO",
                "version": "1.0.0",
                "type": "adapter",
                "interfaces": [{"name": "identity.read", "version": "1.0"}],
                "protocols": ["rest"],
                "capabilities": ["identity.read"],
                "compatibility": {"mnemosyne_api": "^1.0"},
                "scopes": ["identity.read"],
            },
        )
        r = self.client.post(
            "/api/v1/pcip/exchange/accept",
            headers={**self.h, "X-Component-Id": "example.readonly"},
            json={
                "pcip_version": "0.1-proposal",
                "exchange_id": "pcip_ro",
                "level": "L1",
                "from_node": "p",
                "to_node": "local",
                "topic": "t",
                "policy": {
                    "allow_store": True,
                    "allow_forward": False,
                    "allow_train": False,
                    "expires_at": "2099-01-01T00:00:00Z",
                },
                "payload_ref": {
                    "kind": "observation",
                    "udm_id": "u",
                    "content_preview": "x",
                },
            },
        )
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
