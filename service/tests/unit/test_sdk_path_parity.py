# -*- coding: utf-8 -*-
"""P3.1-B: Python / TS SDK Foundation path parity."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class SdkPathParityTests(unittest.TestCase):
    def test_foundation_paths_match(self) -> None:
        py_paths = ROOT / "packages" / "mnemosyne-sdk" / "src" / "mnemosyne_sdk" / "paths.py"
        ts_paths = ROOT / "packages" / "mnemosyne-sdk-ts" / "src" / "paths.js"
        self.assertTrue(py_paths.is_file())
        self.assertTrue(ts_paths.is_file())

        # load python
        import importlib.util

        spec = importlib.util.spec_from_file_location("sdk_paths", py_paths)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        py = {k: list(v) for k, v in mod.FOUNDATION_PATHS.items()}

        # parse TS object loosely
        text = ts_paths.read_text(encoding="utf-8")
        ts: dict[str, list[str]] = {}
        for m in re.finditer(
            r"(\w+):\s*\[\s*\"(GET|POST|PATCH|DELETE|PUT)\"\s*,\s*\"([^\"]+)\"\s*\]",
            text,
        ):
            ts[m.group(1)] = [m.group(2), m.group(3)]

        self.assertEqual(sorted(py.keys()), sorted(ts.keys()))
        for k in py:
            self.assertEqual(py[k], ts[k], msg=k)

    def test_versions_json_lists_both_sdks(self) -> None:
        data = json.loads(
            (ROOT / "schemas" / "VERSIONS.json").read_text(encoding="utf-8")
        )
        self.assertIn("mnemosyne-sdk", data["sdks"])
        self.assertIn("mnemosyne-sdk-ts", data["sdks"])


if __name__ == "__main__":
    unittest.main()
