"""Camofox web extract plugin — bundled, auto-loaded.

Backed by a user-hosted Camofox anti-detection browser instance
(URL configured via ``CAMOFOX_URL``). Extract-only — pair with a
search provider (searxng, brave-free) for ``web_search`` calls.
"""

from __future__ import annotations

from plugins.web.camofox.provider import CamofoxWebExtractProvider


def register(ctx) -> None:
    """Register the Camofox provider with the plugin context."""
    ctx.register_web_search_provider(CamofoxWebExtractProvider())
