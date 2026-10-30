# -*- coding: utf-8 -*-
"""Documented validator subset behaves as frozen."""
from __future__ import annotations

import unittest

from mnemosyne.interop.schemas import validate_against


class ValidatorSubsetTests(unittest.TestCase):
    def test_supports_required_enum_const_additional(self) -> None:
        schema = {
            "type": "object",
            "required": ["a"],
            "additionalProperties": False,
            "properties": {
                "a": {"type": "string", "const": "ok"},
                "b": {"type": "string", "enum": ["x", "y"]},
            },
        }
        self.assertEqual(validate_against(schema, {"a": "ok", "b": "x"}), [])
        errs = validate_against(schema, {"a": "no", "extra": 1})
        self.assertTrue(any("const" in e for e in errs))
        self.assertTrue(any("unexpected" in e for e in errs))

    def test_ignores_unsupported_minLength(self) -> None:
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string", "minLength": 10}},
        }
        # minLength not enforced in Foundation subset
        self.assertEqual(validate_against(schema, {"a": "short"}), [])


if __name__ == "__main__":
    unittest.main()
