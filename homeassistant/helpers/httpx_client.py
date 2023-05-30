"""Helper for httpx."""
from __future__ import annotations

from collections.abc import Callable
import sys
import os
from typing import Any

import httpx
from typing_extensions import Self

from homeassistant.const import APPLICATION_NAME, EVENT_HOMEASSISTANT_CLOSE, __version__
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.loader import bind_hass
from homeassistant.util.ssl import (
    SSLCipherList,
    client_context,
    create_no_verify_ssl_context,
)

from .frame import warn_use

DATA_ASYNC_CLIENT = "httpx_async_client"
DATA_ASYNC_CLIENT_NOVERIFY = "httpx_async_client_noverify"
SERVER_SOFTWARE = "{0}/{1} httpx/{2} Python/{3[0]}.{3[1]}".format(
    APPLICATION_NAME, __version__, httpx.__version__, sys.version_info
)
USER_AGENT = "User-Agent"


@callback
@bind_hass
def get_async_client(hass: HomeAssistant, verify_ssl: bool = True) -> httpx.AsyncClient:
    """Return default httpx AsyncClient.

    This method must be run in the event loop.
    """
    key = DATA_ASYNC_CLIENT if verify_ssl else DATA_ASYNC_CLIENT_NOVERIFY

    client: httpx.AsyncClient | None = hass.data.get(key)

    if client is None:
        client = hass.data[key] = create_async_httpx_client(hass, verify_ssl)

    return client


class HassHttpXAsyncClient(httpx.AsyncClient):
    """httpx AsyncClient that suppresses context management."""

    async def __aenter__(self) -> Self:
        """Prevent an integration from reopen of the client via context manager."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Prevent an integration from close of the client via context manager."""


@callback
def create_async_httpx_client(
    hass: HomeAssistant,
    verify_ssl: bool = True,
    auto_cleanup: bool = True,
    ssl_cipher_list: SSLCipherList = SSLCipherList.PYTHON_DEFAULT,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Create a new httpx.AsyncClient with kwargs, i.e. for cookies.

    If auto_cleanup is False, the client will be
    automatically closed on homeassistant_stop.

    This method must be run in the event loop.
    """
    ssl_context = (
        client_context(ssl_cipher_list)
        if verify_ssl
        else create_no_verify_ssl_context(ssl_cipher_list)
    )

    # Check proxies in environment variables
    http_proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    https_proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    proxies = None
    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy

    client = HassHttpXAsyncClient(
        verify=ssl_context,
        headers={USER_AGENT: SERVER_SOFTWARE},
        proxies=proxies,
        **kwargs,
    )

    original_aclose = client.aclose

    client.aclose = warn_use(  # type: ignore[method-assign]
        client.aclose, "closes the Home Assistant httpx client"
    )

    if auto_cleanup:
        _async_register_async_client_shutdown(hass, client, original_aclose)

    return client


@callback
def _async_register_async_client_shutdown(
    hass: HomeAssistant,
    client: httpx.AsyncClient,
    original_aclose: Callable[..., Any],
) -> None:
    """Register httpx AsyncClient aclose on Home Assistant shutdown.

    This method must be run in the event loop.
    """

    async def _async_close_client(event: Event) -> None:
        """Close httpx client."""
        await original_aclose()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, _async_close_client)
