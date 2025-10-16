"""
Network access guard to ensure only the official OpenAI API endpoint is reachable.

This module monkey-patches popular HTTP/WebSocket clients used within the
application so that any outbound request to hosts other than `api.openai.com`
is rejected immediately. The goal is to harden the deployment and prevent
accidental or malicious connections to third-party services.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional, Tuple
from urllib.parse import urlparse

ALLOWED_HOSTS = {"api.openai.com"}
ALLOWED_SCHEMES = {"https", "wss"}

try:
    from yarl import URL as YarlURL  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YarlURL = None


class NetworkAccessError(RuntimeError):
    """Raised when a blocked outbound network request is attempted."""


def _extract_host_and_scheme(url: Any) -> Tuple[Optional[str], Optional[str]]:
    if url is None:
        return None, None

    if YarlURL is not None and isinstance(url, YarlURL):
        host = url.host
        scheme = url.scheme
    elif hasattr(url, "host") and hasattr(url, "scheme"):
        # Handles httpx.URL and similar classes
        host = getattr(url, "host")
        scheme = getattr(url, "scheme")
    else:
        parsed = urlparse(str(url))
        host = parsed.hostname
        scheme = parsed.scheme

    host = host.lower() if isinstance(host, str) else host
    scheme = scheme.lower() if isinstance(scheme, str) else scheme
    return host, scheme


def _ensure_allowed(target_url: Any, base_url: Any = None) -> None:
    host, scheme = _extract_host_and_scheme(target_url)

    if host is None and base_url is not None:
        host, scheme = _extract_host_and_scheme(base_url)

    if host is None:
        raise NetworkAccessError("Blocked network request: unable to resolve host")

    if host not in ALLOWED_HOSTS:
        raise NetworkAccessError(
            f"Blocked network request to disallowed host '{host}'. "
            "Only api.openai.com is permitted."
        )

    if scheme and scheme not in ALLOWED_SCHEMES:
        raise NetworkAccessError(
            f"Blocked network request using unsupported scheme '{scheme}'. "
            "Only HTTPS/WSS are permitted."
        )


def _guard_requests() -> None:
    try:
        import requests  # type: ignore
    except Exception:  # pragma: no cover - dependency missing
        return

    original_request = requests.sessions.Session.request

    @functools.wraps(original_request)
    def guarded_request(self, method: str, url: Any, *args: Any, **kwargs: Any):
        _ensure_allowed(url)
        return original_request(self, method, url, *args, **kwargs)

    requests.sessions.Session.request = guarded_request  # type: ignore[attr-defined]


def _guard_httpx() -> None:
    try:
        import httpx  # type: ignore
    except Exception:  # pragma: no cover - dependency missing
        return

    original_client_request = httpx.Client.request
    original_async_client_request = httpx.AsyncClient.request

    @functools.wraps(original_client_request)
    def guarded_client_request(
        self, method: str, url: Any, *args: Any, **kwargs: Any
    ):
        _ensure_allowed(url, getattr(self, "base_url", None))
        return original_client_request(self, method, url, *args, **kwargs)

    @functools.wraps(original_async_client_request)
    async def guarded_async_client_request(
        self, method: str, url: Any, *args: Any, **kwargs: Any
    ):
        _ensure_allowed(url, getattr(self, "base_url", None))
        return await original_async_client_request(self, method, url, *args, **kwargs)

    httpx.Client.request = guarded_client_request  # type: ignore[assignment]
    httpx.AsyncClient.request = guarded_async_client_request  # type: ignore[assignment]


def _guard_aiohttp() -> None:
    try:
        import aiohttp  # type: ignore
    except Exception:  # pragma: no cover - dependency missing
        return

    original_request = aiohttp.ClientSession._request
    original_init = aiohttp.ClientSession.__init__

    @functools.wraps(original_request)
    async def guarded_request(self, method: str, str_or_url: Any, *args: Any, **kwargs: Any):
        _ensure_allowed(str_or_url, getattr(self, "_base_url", None))
        return await original_request(self, method, str_or_url, *args, **kwargs)

    @functools.wraps(original_init)
    def guarded_init(self, *args: Any, **kwargs: Any):
        base_url = kwargs.get("base_url")
        if base_url is not None:
            _ensure_allowed(base_url)
        return original_init(self, *args, **kwargs)

    aiohttp.ClientSession._request = guarded_request  # type: ignore[assignment]
    aiohttp.ClientSession.__init__ = guarded_init  # type: ignore[assignment]


def _guard_websocket_clients() -> None:
    try:
        import websocket  # type: ignore
    except Exception:  # pragma: no cover - dependency missing
        websocket = None

    if websocket is not None:
        original_ws_connect = websocket.WebSocket.connect
        original_create_connection = websocket.create_connection

        @functools.wraps(original_ws_connect)
        def guarded_ws_connect(self, url: Any, *args: Any, **kwargs: Any):
            _ensure_allowed(url)
            return original_ws_connect(self, url, *args, **kwargs)

        @functools.wraps(original_create_connection)
        def guarded_create_connection(*args: Any, **kwargs: Any):
            url = args[0] if args else kwargs.get("url")
            _ensure_allowed(url)
            return original_create_connection(*args, **kwargs)

        websocket.WebSocket.connect = guarded_ws_connect  # type: ignore[assignment]
        websocket.create_connection = guarded_create_connection  # type: ignore[assignment]

    try:
        import websockets  # type: ignore
    except Exception:  # pragma: no cover - dependency missing
        return

    original_ws_connect_async = websockets.client.connect

    @functools.wraps(original_ws_connect_async)
    async def guarded_ws_connect_async(*args: Any, **kwargs: Any):
        uri = kwargs.get("uri")
        if uri is None and args:
            uri = args[0]
        _ensure_allowed(uri)
        return await original_ws_connect_async(*args, **kwargs)

    websockets.client.connect = guarded_ws_connect_async  # type: ignore[assignment]


def apply_network_restrictions() -> None:
    """
    Install network guards exactly once.

    The function is idempotent so it can be called from multiple modules without
    risking double-patching.
    """

    if getattr(apply_network_restrictions, "_installed", False):
        return

    _guard_requests()
    _guard_httpx()
    _guard_aiohttp()
    _guard_websocket_clients()

    setattr(apply_network_restrictions, "_installed", True)
