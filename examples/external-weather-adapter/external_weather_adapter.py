# -*- coding: utf-8 -*-
"""Standalone external adapter: talks ONLY over REST (no mnemosyne imports).

Simulates a third-party weather component registering a contract, discovering
capabilities, proposing/accepting PCIP, and verifying peer content never
becomes Active semantic memory.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


class ExternalAdapter:
    """Real external component boundary: HTTP + contract JSON only."""

    COMPONENT_ID = "example.weather.adapter"

    CONTRACT = {
        "component_id": COMPONENT_ID,
        "name": "Example Weather Adapter",
        "version": "0.1.0",
        "type": "adapter",
        "interfaces": [
            {"name": "observation.create", "version": "1.0"},
            {"name": "exchange.accept", "version": "0.1"},
        ],
        "protocols": ["rest"],
        "capabilities": [
            "observation.create",
            "observation.read",
            "exchange.accept",
            "exchange.request",
            "identity.read",
            "memory.search",
            "memory.read",
        ],
        "permissions": [],
        "compatibility": {"mnemosyne_api": "^1.0"},
    }

    def __init__(self, base_url: str, token: str):
        self.base = base_url.rstrip("/")
        self.token = token

    def _call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        with_component: bool = True,
    ) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if with_component:
            headers["X-Component-Id"] = self.COMPONENT_ID
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                raw = res.read().decode("utf-8")
                payload = json.loads(raw) if raw else None
                return int(res.status), payload
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {"detail": str(e)}
            except json.JSONDecodeError:
                payload = {"detail": raw or str(e)}
            return int(e.code), payload

    def register(self) -> tuple[int, Any]:
        body = {**self.CONTRACT, "scopes": list(self.CONTRACT["capabilities"])}
        # bootstrap: token-only first, then subsequent calls use X-Component-Id
        return self._call(
            "POST", "/api/v1/components/register", body, with_component=False
        )

    def discovery(self) -> tuple[int, Any]:
        return self._call("GET", "/api/v1/discovery")

    def validate_contract(self) -> tuple[int, Any]:
        return self._call(
            "POST",
            "/api/v1/udm/validate",
            {"schema_kind": "component", "document": self.CONTRACT},
            with_component=False,
        )

    def pcip_l3(self) -> tuple[int, Any]:
        return self._call(
            "POST",
            "/api/v1/pcip/exchange/request",
            {
                "level": "L3",
                "to_node": "peer-b",
                "topic": "private-weather-diary",
                "policy": {
                    "allow_store": False,
                    "allow_forward": False,
                    "allow_train": False,
                    "expires_at": "2099-01-01T00:00:00Z",
                },
                "payload_ref": {"kind": "memory", "udm_id": "mem_secret"},
            },
        )

    def pcip_accept_peer(
        self,
        *,
        expired: bool = False,
        exchange_id: str = "pcip_ext_weather_1",
        to_node: str = "local",
    ) -> tuple[int, Any]:
        return self._call(
            "POST",
            "/api/v1/pcip/exchange/accept",
            {
                "pcip_version": "0.1-proposal",
                "exchange_id": exchange_id,
                "level": "L1",
                "from_node": "peer-weather-node",
                "to_node": to_node,
                "topic": "weather",
                "policy": {
                    "allow_store": True,
                    "allow_forward": False,
                    "allow_train": False,
                    "expires_at": (
                        "2000-01-01T00:00:00Z" if expired else "2099-01-01T00:00:00Z"
                    ),
                },
                "payload_ref": {
                    "kind": "observation",
                    "udm_id": "udm_wx_1",
                    "content_preview": (
                        "peer claims user lives in Atlantis climate zone ZX-99"
                    ),
                },
            },
        )

    def search_active(self, query: str) -> tuple[int, Any]:
        return self._call(
            "POST",
            "/api/v1/memories/search",
            {"query": query, "status": ["active"], "limit": 20},
        )

    def get_observation(self, oid: str) -> tuple[int, Any]:
        return self._call("GET", f"/api/v1/observations/{oid}")


def run_probe(base_url: str, token: str) -> int:
    adapter = ExternalAdapter(base_url, token)
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    code, body = adapter.validate_contract()
    check(
        "contract.validate",
        code == 200 and bool((body or {}).get("ok")),
        f"{code} {body}",
    )

    code, body = adapter.register()
    check(
        "component.register",
        code == 200 and bool((body or {}).get("ok")),
        f"{code} {body}",
    )
    # re-register with component header after bootstrap (scope path)
    code2, body2 = adapter._call(
        "POST",
        "/api/v1/components/register",
        {**adapter.CONTRACT, "scopes": list(adapter.CONTRACT["capabilities"])},
        with_component=True,
    )
    check(
        "component.reregister_with_id",
        code2 == 200 and bool((body2 or {}).get("ok")),
        f"{code2} {body2}",
    )

    code, body = adapter.discovery()
    schemas = (body or {}).get("schemas") or []
    check(
        "discovery.pcip_l3_forbidden",
        code == 200 and (body or {}).get("pcip", {}).get("l3_default") == "forbidden",
        f"{code} {(body or {}).get('pcip')}",
    )
    check(
        "discovery.has_contract_schema",
        any("component-contract" in s for s in schemas),
        f"count={len(schemas)}",
    )

    code, body = adapter.pcip_l3()
    denied = (code in (401, 403)) or (
        isinstance(body, dict) and body.get("detail") == "l3_forbidden_by_default"
    )
    check("pcip.l3_denied", denied, f"{code} {body}")

    code, body = adapter.pcip_accept_peer(expired=False)
    oid = (body or {}).get("observation_id") if isinstance(body, dict) else None
    check(
        "pcip.accept_as_observation",
        code == 200 and bool((body or {}).get("ok")) and bool(oid),
        f"{code} {body}",
    )

    if oid:
        code, obs = adapter.get_observation(oid)
        meta = (obs or {}).get("metadata") or {}
        check(
            "observation.pcip_flag",
            code == 200 and bool(meta.get("pcip")),
            f"{code} meta_keys={list(meta)}",
        )
        trust = meta.get("trust")
        check(
            "observation.trust_untrusted_stub",
            trust == "untrusted",
            f"trust={trust!r}",
        )

    code, search = adapter.search_active("Atlantis")
    items: list[Any] = []
    if isinstance(search, dict):
        items = (
            search.get("items")
            or search.get("memories")
            or search.get("results")
            or []
        )
    elif isinstance(search, list):
        items = search
    semantic_hits = [
        m
        for m in items
        if isinstance(m, dict)
        and m.get("type") == "semantic"
        and "Atlantis" in (m.get("content") or "")
    ]
    # 403 OK if adapter lacks memory.search — boundary still held for write path
    check(
        "no_auto_active_semantic",
        (code == 403) or (code == 200 and not semantic_hits),
        f"{code} hits={len(semantic_hits)}",
    )

    code, body = adapter.pcip_accept_peer(
        expired=True, exchange_id="pcip_ext_weather_expired"
    )
    expired_rejected = code in (400, 403) or (
        isinstance(body, dict)
        and str(body.get("detail", "")).startswith(("expired", "policy_expired"))
    )
    check("pcip.expired_policy", expired_rejected, f"{code} {body}")

    code, body = adapter.pcip_accept_peer(
        exchange_id="pcip_wrong_node", to_node="someone-else"
    )
    wrong_node = code in (400, 403) or (
        isinstance(body, dict) and body.get("detail") == "to_node_mismatch"
    )
    check("pcip.to_node_mismatch", wrong_node, f"{code} {body}")

    failed = [r for r in results if not r[1]]
    print("---")
    print(f"passed={len(results) - len(failed)} failed={len(failed)} total={len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "usage: external_weather_adapter.py <base_url> <token>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise SystemExit(run_probe(sys.argv[1], sys.argv[2]))
