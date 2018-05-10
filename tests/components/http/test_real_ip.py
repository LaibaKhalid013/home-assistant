"""Test real IP middleware."""
from aiohttp import web
from aiohttp.hdrs import X_FORWARDED_FOR

from homeassistant.components.http.real_ip import setup_real_ip
from homeassistant.components.http.const import KEY_REAL_IP

from .test_auth import TRUSTED_NETWORKS


async def mock_handler(request):
    """Handler that returns the real IP as text."""
    return web.Response(text=str(request[KEY_REAL_IP]))


async def test_ignore_x_forwarded_for(aiohttp_client):
    """Test that we get the IP from the transport."""
    app = web.Application()
    app.router.add_get('/', mock_handler)
    setup_real_ip(app, False, TRUSTED_NETWORKS)

    mock_api_client = await aiohttp_client(app)

    resp = await mock_api_client.get('/', headers={
        X_FORWARDED_FOR: '255.255.255.255'
    })
    assert resp.status == 200
    text = await resp.text()
    assert text != '255.255.255.255'


async def test_use_x_forwarded_for(aiohttp_client):
    """Test that we get the IP from the transport."""
    app = web.Application()
    app.router.add_get('/', mock_handler)
    setup_real_ip(app, True, TRUSTED_NETWORKS)

    mock_api_client = await aiohttp_client(app)

    resp = await mock_api_client.get('/', headers={
        X_FORWARDED_FOR: '255.255.255.255'
    })
    assert resp.status == 200
    text = await resp.text()
    assert text == '255.255.255.255'
