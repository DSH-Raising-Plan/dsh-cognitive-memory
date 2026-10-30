# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

import httpx


class MnemosyneClient:
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
        return self.request("GET", "/api/v1/health")

    def discovery(self) -> Any:
        return self.request("GET", "/api/v1/discovery")

    def observe(self, content: str, *, source_kind: str = "dialog", **extra: Any) -> Any:
        body = {"content": content, "source_kind": source_kind, "producer": "sdk.python", **extra}
        return self.request("POST", "/api/v1/observations", body)

    def retrieve(self, query: str, **extra: Any) -> Any:
        return self.request("POST", "/api/v1/retrieve", {"query": query, **extra})

    def search(self, query: str, limit: int = 10) -> Any:
        return self.request("POST", "/api/v1/memories/search", {"query": query, "limit": limit})
