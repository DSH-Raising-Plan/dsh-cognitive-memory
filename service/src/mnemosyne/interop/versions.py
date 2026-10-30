# -*- coding: utf-8 -*-
"""Foundation 版本基线加载（Schema / API / PCIP 独立版本）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mnemosyne.interop.schemas import schema_root


def load_version_baseline() -> dict[str, Any]:
    path = schema_root() / "VERSIONS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def discovery_versions_payload() -> dict[str, Any]:
    baseline = load_version_baseline()
    return {
        "baseline": baseline.get("baseline"),
        "mnemosyne_api": (baseline.get("api") or {}).get("mnemosyne_api", "v1"),
        "schemas": baseline.get("schemas") or {},
        "pcip": baseline.get("pcip") or {},
        "sdks": baseline.get("sdks") or {},
    }
