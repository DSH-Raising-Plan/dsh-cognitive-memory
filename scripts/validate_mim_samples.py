"""Validate samples/providers/**/mapped.mim.json against MIM 0.1 schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "memory-interchange" / "v0.1.json"
SAMPLES = ROOT / "samples" / "providers"


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    paths = sorted(SAMPLES.glob("*/mapped.mim.json"))
    if not paths:
        print("no mapped.mim.json found", file=sys.stderr)
        return 1
    errors = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        errs = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errs:
            errors += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for e in errs:
                loc = ".".join(str(p) for p in e.path) or "<root>"
                print(f"  - {loc}: {e.message}")
        else:
            n = len(data.get("items") or [])
            print(f"OK   {path.relative_to(ROOT)} ({n} items)")
    if errors:
        print(f"{errors} bundle(s) failed", file=sys.stderr)
        return 1
    print(f"all {len(paths)} MIM bundles valid against 0.1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
