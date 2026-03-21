"""Async ActiveCampaign API v3 client."""

import asyncio
import time
from typing import Any

import httpx


class ActiveCampaignError(Exception):
    """ActiveCampaign API error with status code and details."""

    def __init__(self, message: str, status: int, errors: list[dict] | None = None):
        self.message = message
        self.status = status
        self.errors = errors or []
        super().__init__(f"{status}: {message}")


class ActiveCampaignClient:
    """Lightweight async client for the ActiveCampaign API v3.

    Auth: Api-Token header.
    Rate limit: 5 req/s per account — enforced client-side.
    """

    MAX_RPS = 5
    MIN_INTERVAL = 1.0 / MAX_RPS  # 0.2s between requests

    def __init__(self, base_url: str, api_key: str):
        # Normalize: strip trailing slash, ensure /api/3 suffix
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/api/3"):
            base_url = f"{base_url}/api/3"
        self.base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Api-Token": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        """Enforce 5 req/s rate limit."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.MIN_INTERVAL:
                await asyncio.sleep(self.MIN_INTERVAL - elapsed)
            self._last_request = time.monotonic()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        await self._throttle()
        resp = await self._client.request(method, path, **kwargs)

        if resp.status_code == 204:
            return {"success": True}

        try:
            data = resp.json()
        except Exception:
            data = {}

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            await asyncio.sleep(retry_after)
            return await self._request(method, path, **kwargs)

        if resp.status_code >= 400:
            # AC returns errors in various formats
            msg = data.get("message", "")
            if not msg:
                errors = data.get("errors", [])
                if errors:
                    msg = "; ".join(
                        e.get("title", "") or e.get("detail", "")
                        for e in errors
                    )
                else:
                    msg = resp.text[:500]
            raise ActiveCampaignError(
                msg, resp.status_code, data.get("errors")
            )

        return data

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json=json or {})

    async def put(self, path: str, json: dict[str, Any]) -> Any:
        return await self._request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    async def close(self) -> None:
        await self._client.aclose()
