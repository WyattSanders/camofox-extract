"""Core extraction logic — extract clean content from URLs via Camofox."""

from __future__ import annotations

import re
from typing import Any, Optional

from camofox_extract.client import CamofoxClient, CamofoxError
from camofox_extract.markdown import accessibility_tree_to_markdown


def _extract_title(snapshot: str) -> str:
    """Extract the page title from the first Heading node in the snapshot."""
    for line in snapshot.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Match: - heading "Title" [level=N]
        m = re.match(r'^-\s+heading\s+"([^"]*)"', stripped)
        if m:
            return m.group(1)
        # Match: - heading: Title (unquoted)
        m = re.match(r'^-\s+heading:\s*(.+)', stripped)
        if m:
            return m.group(1).strip()
    return ""


def extract_url(
    url: str,
    client: CamofoxClient,
    timeout: int = 30,
    wait_for_network: bool = True,
) -> dict[str, Any]:
    """Extract content from a single URL.

    Returns a dict with keys: url, title, content, raw_content, error.
    """
    result: dict[str, Any] = {
        "url": url,
        "title": "",
        "content": "",
        "raw_content": "",
        "error": None,
    }

    try:
        tab_id = client.create_tab()
        try:
            client.navigate(tab_id, url)
            client.wait_for_ready(tab_id, timeout=timeout, wait_for_network=wait_for_network)
            raw_snapshot = client.snapshot(tab_id)
            result["raw_content"] = raw_snapshot
            result["title"] = _extract_title(raw_snapshot)
            result["content"] = accessibility_tree_to_markdown(raw_snapshot)
        finally:
            client.close_tab(tab_id)

    except CamofoxError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


def extract_urls(
    urls: list[str],
    camofox_url: Optional[str] = None,
    camofox_api_key: Optional[str] = None,
    timeout: int = 30,
    wait_for_network: bool = True,
    client: Optional[CamofoxClient] = None,
) -> list[dict[str, Any]]:
    """Extract content from multiple URLs.

    Args:
        urls: List of URLs to extract.
        camofox_url: Camofox server URL (or env CAMOFOX_URL).
        camofox_api_key: API key (or env CAMOFOX_API_KEY).
        timeout: Navigation timeout in seconds.
        wait_for_network: Whether to wait for network idle.
        optional client: Pre-existing client to use (creates one if None).

    Returns:
        List of dicts with keys: url, title, content, raw_content, error.
    """
    own_client = client is None
    if own_client:
        client = CamofoxClient(base_url=camofox_url, api_key=camofox_api_key)

    try:
        results = []
        for url in urls:
            results.append(extract_url(url, client, timeout=timeout, wait_for_network=wait_for_network))
        return results
    finally:
        if own_client:
            client.cleanup()
