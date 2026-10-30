# -*- coding: utf-8 -*-
"""Emit Foundation stability report (CI artifact / local)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "service" / "src") + os.pathsep + env.get(
        "PYTHONPATH", ""
    )
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def _write_md(
    *,
    baseline: dict,
    unit_ok: bool,
    probe_ok: bool,
    generated_at: str,
) -> Path:
    out_dir = ROOT / "docs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "FOUNDATION_STABILITY_LATEST.md"
    versions_json = json.dumps(baseline, ensure_ascii=False, indent=2)
    md = f"""# Foundation Stability Report

Generated: `{generated_at}`  
Baseline: **`{baseline.get("baseline")}`**

## Results

| Check | OK |
| --- | --- |
| Unit tests | {"PASS" if unit_ok else "FAIL"} |
| External interop probe (12) | {"PASS" if probe_ok else "FAIL"} |

## Versions

```json
{versions_json}
```

## Known limits

See [`FOUNDATION_KNOWN_LIMITS.md`](../FOUNDATION_KNOWN_LIMITS.md).

## Notes

- Acceptance freeze: [`P3_FOUNDATION_ACCEPTANCE.md`](../P3_FOUNDATION_ACCEPTANCE.md)
- Stabilization plan: [`P3.1_FOUNDATION_STABILIZATION.md`](../P3.1_FOUNDATION_STABILIZATION.md)
- Compatibility matrix: [`FOUNDATION_COMPATIBILITY_MATRIX.md`](../FOUNDATION_COMPATIBILITY_MATRIX.md)
"""
    md_path.write_text(md, encoding="utf-8")
    return md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Only write report; use --unit-ok/--probe-ok (for CI after prior steps)",
    )
    parser.add_argument("--unit-ok", action="store_true", default=False)
    parser.add_argument("--probe-ok", action="store_true", default=False)
    args = parser.parse_args(argv)

    baseline = json.loads((ROOT / "schemas" / "VERSIONS.json").read_text(encoding="utf-8"))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.skip_tests:
        unit_ok, probe_ok = bool(args.unit_ok), bool(args.probe_ok)
        unit_out = probe_out = ""
        unit_rc = 0 if unit_ok else 1
        probe_rc = 0 if probe_ok else 1
    else:
        unit_rc, unit_out = _run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "service/tests/unit",
                "-q",
            ]
        )
        probe_rc, probe_out = _run(
            [sys.executable, "scripts/run_external_interop_probe.py"]
        )
        unit_ok, probe_ok = unit_rc == 0, probe_rc == 0

    md_path = _write_md(
        baseline=baseline,
        unit_ok=unit_ok,
        probe_ok=probe_ok,
        generated_at=generated_at,
    )
    print(
        json.dumps(
            {"ok": unit_ok and probe_ok, "md": str(md_path)},
            ensure_ascii=False,
        )
    )
    return 0 if unit_ok and probe_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
