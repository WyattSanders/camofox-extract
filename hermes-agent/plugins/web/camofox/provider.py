"""Camofox web extract — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. Uses the
``camofox-extract`` library to extract clean markdown from any URL through
the Camofox anti-detection Firefox engine.

Extract-only — Camofox is a browser, not a search engine.
``supports_search()`` returns False.

Config keys this provider responds to::

    web:
      extract_backend: "camofox"     # explicit per-capability

Env vars::

    CAMOFOX_URL=http://localhost:9377
    CAMOFOX_API_KEY=...              # optional for localhost
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)


class CamofoxWebExtractProvider(WebSearchProvider):
    """Extract page content via Camofox anti-detection browser."""

    @property
    def name(self) -> str:
        return "camofox"

    @property
    def display_name(self) -> str:
        return "Camofox Extract"

    def is_available(self) -> bool:
        """Return True when ``CAMOFOX_URL`` is set and camofox_extract is importable."""
        if not os.getenv("CAMOFOX_URL", "").strip():
            return False
        try:
            import camofox_extract  # noqa: F401 — verify import works
            return True
        except ImportError:
            return False

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract content from one or more URLs via Camofox browser.

        Each URL is opened in a real Firefox tab, rendered with JS, and the
        accessibility tree is converted to clean markdown. Handles Cloudflare,
        bot detection, and dynamic content automatically.

        Returns the legacy per-URL list-of-results shape. Per-URL failures
        become items with an ``error`` field.
        """
        from camofox_extract import extract_urls as _extract_urls

        camofox_url = os.getenv("CAMOFOX_URL", "").strip().rstrip("/")
        api_key = os.getenv("CAMOFOX_API_KEY", "").strip()
        timeout = kwargs.get("timeout", 30)

        if not camofox_url:
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "error": "CAMOFOX_URL is not set",
                }
                for url in urls
            ]

        # Default format requests
        # kwargs may carry `format` for forward compat
        try:
            results = _extract_urls(
                urls=list(urls),
                camofox_url=camofox_url,
                camofox_api_key=api_key or None,
                timeout=timeout,
                wait_for_network=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Camofox extract error: %s", exc)
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "error": f"Camofox extract failed: {exc}",
                }
                for url in urls
            ]

        # Normalize to the provider contract shape
        normalized: List[Dict[str, Any]] = []
        for r in results:
            normalized.append(
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "raw_content": r.get("raw_content", ""),
                    "error": r.get("error"),
                }
            )

        return normalized

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Camofox Extract",
            "badge": "self-hosted · browser",
            "tag": (
                "Extract markdown from any URL via Camofox anti-detection "
                "browser. Requires CAMOFOX_URL pointing at your instance."
            ),
            "env_vars": [
                {
                    "key": "CAMOFOX_URL",
                    "prompt": "Camofox server URL (e.g. http://localhost:9377)",
                    "url": "https://github.com/jo-inc/camofox-browser",
                },
                {
                    "key": "CAMOFOX_API_KEY",
                    "prompt": "Camofox API key (optional for localhost)",
                    "url": "",
                },
            ],
        }
