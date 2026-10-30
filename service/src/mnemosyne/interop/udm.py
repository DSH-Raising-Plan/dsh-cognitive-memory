# -*- coding: utf-8 -*-
"""Universal Data Model：在本地对象与 UDM 信封之间映射。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def observation_to_udm(obs: dict[str, Any], *, source_node: str = "local") -> dict[str, Any]:
    return {
        "udm_version": "1.0",
        "kind": "observation",
        "id": obs["id"],
        "recorded_at": obs.get("created_at") or _now(),
        "event_time": obs.get("occurred_at"),
        "canonical": {
            "content": obs.get("content") or "",
            "status": obs.get("status") or "observed",
            "type": obs.get("source_kind"),
        },
        "extensions": {},
        "original_payload": None,
        "external_ids": {},
        "provenance": {
            "producer": obs.get("producer") or "unknown",
            "source_node": source_node,
            "correlation_id": obs.get("correlation_id"),
            "trust": "local",
        },
        "schema_version": "1.0",
    }


def memory_to_udm(mem: dict[str, Any], *, source_node: str = "local") -> dict[str, Any]:
    return {
        "udm_version": "1.0",
        "kind": "memory",
        "id": mem["id"],
        "recorded_at": mem.get("updated_at") or mem.get("created_at") or _now(),
        "event_time": mem.get("event_time"),
        "canonical": {
            "content": mem.get("content") or "",
            "status": mem.get("status"),
            "type": mem.get("type"),
        },
        "extensions": {"mnemosyne": {"version": mem.get("version"), "confidence": mem.get("confidence")}},
        "original_payload": None,
        "external_ids": {},
        "provenance": {
            "producer": "mnemosyne",
            "source_node": source_node,
            "correlation_id": None,
            "trust": "local",
        },
        "schema_version": "1.0",
    }
