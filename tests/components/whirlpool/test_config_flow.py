"""Test the Whirlpool Sixth Sense config flow."""
import asyncio
from unittest.mock import patch

import aiohttp

from homeassistant import config_entries
from homeassistant.components.whirlpool.const import DOMAIN

from tests.common import MockConfigEntry

CONFIG_INPUT = {
    "username": "test-username",
    "password": "test-password",
}


async def test_form(hass, region):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == config_entries.SOURCE_USER

    with patch("homeassistant.components.whirlpool.config_flow.Auth.do_auth"), patch(
        "homeassistant.components.whirlpool.config_flow.Auth.is_access_token_valid",
        return_value=True,
    ), patch(
        "homeassistant.components.whirlpool.config_flow.BackendSelector"
    ) as mock_backend_selector, patch(
        "homeassistant.components.whirlpool.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
        "region": region[0],
    }
    assert len(mock_setup_entry.mock_calls) == 1
    mock_backend_selector.assert_called_once_with(region[2], region[1])


async def test_form_invalid_auth(hass, region):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("homeassistant.components.whirlpool.config_flow.Auth.do_auth"), patch(
        "homeassistant.components.whirlpool.config_flow.Auth.is_access_token_valid",
        return_value=False,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass, region):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.whirlpool.config_flow.Auth.do_auth",
        side_effect=aiohttp.ClientConnectionError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_auth_timeout(hass, region):
    """Test we handle auth timeout error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.whirlpool.config_flow.Auth.do_auth",
        side_effect=asyncio.TimeoutError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_generic_auth_exception(hass, region):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.whirlpool.config_flow.Auth.do_auth",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}


async def test_form_already_configured(hass, region):
    """Test we handle cannot connect error."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-username", "password": "test-password"},
        unique_id="test-username",
    )
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == config_entries.SOURCE_USER

    with patch("homeassistant.components.whirlpool.config_flow.Auth.do_auth"), patch(
        "homeassistant.components.whirlpool.config_flow.Auth.is_access_token_valid",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG_INPUT | {"region": region[0]},
        )
        await hass.async_block_till_done()

    assert result2["type"] == "abort"
    assert result2["reason"] == "already_configured"
