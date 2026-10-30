# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from mnemosyne.interop.schemas import (
    schema_root,
    validate_component_contract,
    validate_pcip_exchange,
    validate_udm,
)
from mnemosyne.interop.udm import observation_to_udm


class InteropSchemaTests(unittest.TestCase):
    def test_schema_root_exists(self) -> None:
        root = schema_root()
        self.assertTrue((root / "component-contract" / "v1.json").is_file())
        self.assertTrue((root / "pcip" / "exchange-v1.json").is_file())

    def test_component_contract_ok_and_bad(self) -> None:
        ok = validate_component_contract(
            {
                "component_id": "example.adapter",
                "name": "Example",
                "version": "1.0.0",
                "type": "adapter",
                "interfaces": [{"name": "memory.read", "version": "1.0"}],
                "protocols": ["rest", "mcp"],
                "capabilities": ["memory.read"],
                "permissions": [],
                "compatibility": {"mnemosyne_api": "^1.0"},
            }
        )
        self.assertTrue(ok["ok"], ok)
        bad = validate_component_contract({"component_id": "X"})
        self.assertFalse(bad["ok"])

    def test_udm_observation_roundtrip_shape(self) -> None:
        udm = observation_to_udm(
            {
                "id": "obs_1",
                "content": "hello",
                "created_at": "2026-01-01T00:00:00Z",
                "occurred_at": None,
                "producer": "test",
                "source_kind": "dialog",
                "status": "observed",
            }
        )
        check = validate_udm(udm)
        self.assertTrue(check["ok"], check)

    def test_pcip_l1_shape(self) -> None:
        doc = {
            "pcip_version": "0.1-proposal",
            "exchange_id": "pcip_1",
            "level": "L1",
            "from_node": "node-a",
            "to_node": "node-b",
            "topic": "music",
            "policy": {
                "allow_store": True,
                "allow_forward": False,
                "allow_train": False,
                "expires_at": "2099-01-01T00:00:00Z",
            },
            "payload_ref": {"kind": "observation", "udm_id": "obs_x", "content_preview": "likes music"},
        }
        self.assertTrue(validate_pcip_exchange(doc)["ok"])


if __name__ == "__main__":
    unittest.main()
