#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/service/src${PYTHONPATH:+:$PYTHONPATH}"
pip install -e ./service
pip install httpx uvicorn fastapi pydantic
python -m unittest discover -s service/tests/unit -v
python scripts/run_external_interop_probe.py
python scripts/generate_foundation_stability_report.py --skip-tests --unit-ok --probe-ok
echo "foundation CI script OK"
