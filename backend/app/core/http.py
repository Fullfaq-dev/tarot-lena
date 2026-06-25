"""Shared async HTTP client.

Creating a fresh ``httpx.AsyncClient`` per request forces a new TCP + TLS
handshake every time, which adds hundreds of milliseconds to every AI chat
message, media generation poll, upload, and download. A single pooled client
with keep-alive reuses warm connections across all calls, which is the main
latency win for the bot's heavy flows.
"""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None

_LIMITS = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0,
)
# Generous default; individual calls override via the per-request ``timeout=``.
_DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def get_async_client() -> httpx.AsyncClient:
    """Return a process-wide pooled async HTTP client (lazily created)."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            limits=_LIMITS,
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=True,
        )
    return _client


async def aclose_async_client() -> None:
    """Close the shared client (call on application shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
