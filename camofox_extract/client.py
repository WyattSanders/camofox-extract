"""Camofox REST API client."""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

import requests


class CamofoxError(Exception):
    """Base exception for Camofox client errors."""


class CamofoxConnectionError(CamofoxError):
    """Could not connect to Camofox server."""


class CamofoxAPIError(CamofoxError):
    """Camofox API returned an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class CamofoxClient:
    """Client for the Camofox anti-detection browser REST API.

    Usage::

        with CamofoxClient() as client:
            tab_id = client.create_tab()
            client.navigate(tab_id, "https://example.com")
            client.wait_for_ready(tab_id)
            snapshot = client.snapshot(tab_id)
            client.close_tab(tab_id)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.base_url = (base_url or os.environ.get("CAMOFOX_URL", "http://localhost:9377")).rstrip("/")
        self.api_key = api_key or os.environ.get("CAMOFOX_API_KEY", "")
        self.user_id = user_id or os.environ.get("CAMOFOX_USER_ID", f"camofox-extract-{uuid.uuid4().hex[:12]}")
        self.session_key = "default"
        self._session = requests.Session()
        self._tabs: list[str] = []

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method,
                url,
                json=json_data,
                params=params,
                headers=self._headers(),
                timeout=timeout,
            )
        except requests.ConnectionError as e:
            raise CamofoxConnectionError(
                f"Cannot connect to Camofox at {self.base_url}. "
                f"Is the server running? Error: {e}"
            ) from e
        except requests.Timeout as e:
            raise CamofoxError(f"Request timed out after {timeout}s: {e}") from e

        if resp.status_code >= 400:
            try:
                body = resp.json()
                msg = body.get("error", body.get("message", resp.text[:200]))
            except Exception:
                msg = resp.text[:200]
            raise CamofoxAPIError(resp.status_code, msg)

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def create_tab(self, url: Optional[str] = None) -> str:
        """Create a new browser tab. Returns the tab ID."""
        data: dict[str, Any] = {"userId": self.user_id, "sessionKey": self.session_key}
        if url:
            data["url"] = url
        result = self._request("POST", "/tabs", json_data=data)
        tab_id = result["tabId"]
        self._tabs.append(tab_id)
        return tab_id

    def navigate(self, tab_id: str, url: str) -> dict[str, Any]:
        """Navigate a tab to a URL."""
        return self._request(
            "POST",
            f"/tabs/{tab_id}/navigate",
            json_data={"userId": self.user_id, "sessionKey": self.session_key, "url": url},
        )

    def wait_for_ready(self, tab_id: str, timeout: int = 30, wait_for_network: bool = True) -> dict[str, Any]:
        """Wait for the page to finish loading."""
        return self._request(
            "POST",
            f"/tabs/{tab_id}/wait",
            json_data={
                "userId": self.user_id,
                "sessionKey": self.session_key,
                "timeout": timeout,
                "waitForNetwork": wait_for_network,
            },
            timeout=timeout + 5,
        )

    def snapshot(self, tab_id: str, timeout: int = 10) -> str:
        """Get the full accessibility tree snapshot for a tab.

        Handles pagination automatically for large pages.
        Returns the concatenated snapshot text.
        """
        parts: list[str] = []
        offset = 0

        while True:
            params: dict[str, Any] = {"userId": self.user_id}
            if offset > 0:
                params["offset"] = offset

            result = self._request(
                "GET",
                f"/tabs/{tab_id}/snapshot",
                params=params,
                timeout=timeout,
            )

            snapshot_text = result.get("snapshot", "")
            if snapshot_text:
                parts.append(snapshot_text)

            if not result.get("hasMore", False):
                break

            next_offset = result.get("nextOffset")
            if next_offset is None:
                break
            offset = next_offset

        return "\n".join(parts)

    def screenshot(self, tab_id: str) -> bytes:
        """Get a PNG screenshot of the tab. Returns raw bytes."""
        url = f"{self.base_url}/tabs/{tab_id}/screenshot"
        try:
            resp = self._session.get(
                url,
                params={"userId": self.user_id},
                headers=self._headers(),
                timeout=15,
            )
        except requests.ConnectionError as e:
            raise CamofoxConnectionError(f"Cannot connect: {e}") from e

        if resp.status_code >= 400:
            raise CamofoxAPIError(resp.status_code, resp.text[:200])
        return resp.content

    def links(self, tab_id: str) -> list[dict[str, str]]:
        """Get all links from the tab."""
        result = self._request(
            "GET",
            f"/tabs/{tab_id}/links",
            params={"userId": self.user_id},
        )
        return result.get("links", [])

    def close_tab(self, tab_id: str) -> None:
        """Close a browser tab."""
        try:
            self._request("DELETE", f"/tabs/{tab_id}")
        except CamofoxError:
            pass  # Tab may already be closed
        if tab_id in self._tabs:
            self._tabs.remove(tab_id)

    def list_tabs(self) -> list[dict[str, Any]]:
        """List all open tabs for this user."""
        result = self._request("GET", "/tabs", params={"userId": self.user_id})
        return result.get("tabs", [])

    def cleanup(self) -> None:
        """Delete the entire session for this user."""
        try:
            self._request("DELETE", f"/sessions/{self.user_id}")
        except CamofoxError:
            pass  # Session may not exist
        self._tabs.clear()

    def __enter__(self) -> "CamofoxClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
