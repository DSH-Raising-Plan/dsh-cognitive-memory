# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

import httpx

from mnemosyne_sdk.paths import FOUNDATION_PATHS


class MnemosyneClient:
    """Thin REST client. Core methods share paths with the TS SDK."""

    PATHS = FOUNDATION_PATHS

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        component_id: str = "sdk.python",
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.component_id = component_id
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Component-Id": self.component_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=json_body,
            )
            res.raise_for_status()
            if res.status_code == 204 or not res.content:
                return None
            return res.json()

    def health(self) -> Any:
        m, p = self.PATHS["health"]
        return self.request(m, p)

    def discovery(self) -> Any:
        m, p = self.PATHS["discovery"]
        return self.request(m, p)

    def observe(self, body: dict[str, Any] | None = None, **extra: Any) -> Any:
        """POST /observations. Prefer body dict (TS-compatible); content= kwargs also OK."""
        payload: dict[str, Any] = dict(body or {})
        payload.update(extra)
        payload.setdefault("producer", self.component_id)
        if "content" in payload and "source_kind" not in payload:
            payload["source_kind"] = "dialog"
        m, p = self.PATHS["observe"]
        return self.request(m, p, payload)

    def retrieve(self, body: dict[str, Any] | None = None, **extra: Any) -> Any:
        payload = dict(body or {})
        payload.update(extra)
        m, p = self.PATHS["retrieve"]
        return self.request(m, p, payload)

    def search(self, body: dict[str, Any] | None = None, **extra: Any) -> Any:
        payload = dict(body or {})
        payload.update(extra)
        m, p = self.PATHS["search"]
        return self.request(m, p, payload)
