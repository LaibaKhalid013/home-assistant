"""Tests for honeywell config flow."""
from unittest.mock import MagicMock, patch

import AIOSomecomfort

from homeassistant import data_entry_flow
from homeassistant.components.honeywell.const import (
    CONF_COOL_AWAY_TEMPERATURE,
    CONF_HEAT_AWAY_TEMPERATURE,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

FAKE_CONFIG = {
    "username": "fake",
    "password": "user",
    "away_cool_temperature": 88,
    "away_heat_temperature": 61,
}


async def test_show_authenticate_form(hass: HomeAssistant, client: MagicMock) -> None:
    """Test that the config form is shown."""
    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_connection_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test that an error message is shown on connection fail."""
    client.login.side_effect = AIOSomecomfort.ConnectionError
    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_auth_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test that an error message is shown on login fail."""
    client.login.side_effect = AIOSomecomfort.AuthError
    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_create_entry(hass: HomeAssistant, client: MagicMock) -> None:
    """Test that the config entry is created."""
    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
        )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG


async def test_show_option_form(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: MagicMock
) -> None:
    """Test that the option form is shown."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_create_option_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: MagicMock
) -> None:
    """Test that the config entry is created."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    with patch("AIOSomecomfort.AIOSomeComfort", return_value=client):
        options_form = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )
        result = await hass.config_entries.options.async_configure(
            options_form["flow_id"],
            user_input={CONF_COOL_AWAY_TEMPERATURE: 1, CONF_HEAT_AWAY_TEMPERATURE: 2},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_COOL_AWAY_TEMPERATURE: 1,
        CONF_HEAT_AWAY_TEMPERATURE: 2,
    }
