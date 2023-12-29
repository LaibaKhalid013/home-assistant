"""Test the Blue Current config flow."""
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.components.blue_current import DOMAIN
from homeassistant.components.blue_current.config_flow import (
    AlreadyConnected,
    InvalidApiToken,
    RequestLimitReached,
    WebsocketError,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(hass: HomeAssistant) -> None:
    """Test if the form is created."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {}


async def test_user(hass: HomeAssistant) -> None:
    """Test if the api token is set."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {}

    with patch("bluecurrent_api.Client.validate_api_token", return_value=True), patch(
        "bluecurrent_api.Client.get_email", return_value="test@email.com"
    ), patch(
        "homeassistant.components.blue_current.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_token": "123",
            },
        )
        await hass.async_block_till_done()

    assert result2["title"] == "test@email.com"
    assert result2["data"] == {"api_token": "123"}


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (InvalidApiToken(), "invalid_token"),
        (RequestLimitReached(), "limit_reached"),
        (AlreadyConnected(), "already_connected"),
        (Exception(), "unknown"),
        (WebsocketError(), "cannot_connect"),
    ],
)
async def test_flow_fails(hass: HomeAssistant, error: Exception, message: str) -> None:
    """Test user initialized flow with invalid username."""
    with patch(
        "bluecurrent_api.Client.validate_api_token",
        side_effect=error,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={"api_token": "123"},
        )
        assert result["errors"]["base"] == message

    with patch("bluecurrent_api.Client.validate_api_token", return_value=True), patch(
        "bluecurrent_api.Client.get_email", return_value="test@email.com"
    ), patch(
        "homeassistant.components.blue_current.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_token": "123",
            },
        )
        await hass.async_block_till_done()

        assert result2["title"] == "test@email.com"
        assert result2["data"] == {"api_token": "123"}


async def test_flow_reauth(hass: HomeAssistant) -> None:
    """Test reauth flow."""
    with patch(
        "bluecurrent_api.Client.validate_api_token",
        return_value=True,
    ), patch("bluecurrent_api.Client.get_email", return_value="test@email.com"):
        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="uuid",
            unique_id="1234",
            data={"api_token": "123"},
        )
        entry.add_to_hass(hass)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
                "unique_id": entry.unique_id,
            },
            data={"api_token": "abc"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_token": "1234567890"},
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert entry.data.copy() == {"api_token": "1234567890"}

        assert await entry.async_unload(hass)
        await hass.async_block_till_done()
