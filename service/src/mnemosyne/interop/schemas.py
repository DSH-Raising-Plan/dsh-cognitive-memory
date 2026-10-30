# -*- coding: utf-8 -*-
"""加载并校验 schemas/ 下的 JSON Schema（无强制依赖 jsonschema 时做轻量检查）。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SCHEMA_ROOT_CANDIDATES = [
    Path(__file__).resolve().parents[4] / "schemas",  # repo root when editable
    Path(__file__).resolve().parents[3] / "schemas",
]


def schema_root() -> Path:
    for p in _SCHEMA_ROOT_CANDIDATES:
        if p.is_dir():
            return p
    # fallback: walk up
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        cand = parent / "schemas"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("schemas/ directory not found")


def load_schema(relative: str) -> dict[str, Any]:
    path = schema_root() / relative
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value: Any, expected: str | list[str]) -> bool:
    types = expected if isinstance(expected, list) else [expected]
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    for t in types:
        if t == "null" and value is None:
            return True
        py = mapping.get(t)
        if py and isinstance(value, py):
            if t == "integer" and isinstance(value, bool):
                continue
            return True
    return False


def validate_against(schema: dict[str, Any], data: Any, *, path: str = "$") -> list[str]:
    """轻量子集校验：required / type / enum / const / properties / additionalProperties=false。"""
    errors: list[str] = []
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
    if "type" in schema and not _type_ok(data, schema["type"]):
        errors.append(f"{path}: type mismatch")
        return errors
    if schema.get("type") == "object" and isinstance(data, dict):
        for key in schema.get("required") or []:
            if key not in data:
                errors.append(f"{path}: missing required {key}")
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in props:
                    errors.append(f"{path}: unexpected property {key}")
        for key, sub in props.items():
            if key in data:
                errors.extend(validate_against(sub, data[key], path=f"{path}.{key}"))
        if "pattern" in schema and isinstance(data.get("component_id", data) if False else None, str):
            pass
    if "pattern" in schema and isinstance(data, str):
        if not re.search(schema["pattern"], data):
            errors.append(f"{path}: pattern mismatch")
    if schema.get("type") == "array" and isinstance(data, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(data):
                errors.extend(validate_against(item_schema, item, path=f"{path}[{i}]"))
    return errors


def validate_component_contract(doc: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("component-contract/v1.json")
    errors = validate_against(schema, doc)
    # pattern on component_id
    cid = doc.get("component_id")
    if isinstance(cid, str) and not re.match(r"^[a-z0-9][a-z0-9._-]*$", cid):
        errors.append("$.component_id: pattern mismatch")
    return {"ok": not errors, "errors": errors}


def validate_udm(doc: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("universal-data-model/v1.json")
    return {"ok": not (errs := validate_against(schema, doc)), "errors": errs}


def validate_pcip_exchange(doc: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("pcip/exchange-v1.json")
    return {"ok": not (errs := validate_against(schema, doc)), "errors": errs}


def validate_event(doc: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("events/v1.json")
    return {"ok": not (errs := validate_against(schema, doc)), "errors": errs}
