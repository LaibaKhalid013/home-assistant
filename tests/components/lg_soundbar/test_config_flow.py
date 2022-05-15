"""Test the lg_soundbar config flow."""
from unittest.mock import patch

from homeassistant.components.lg_soundbar.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_UNIQUE_ID

from tests.common import MockConfigEntry


async def test_form(hass):
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.lg_soundbar.config_flow.LGSoundbarConfigFlow.test_connect",
        return_value="uuid",
    ), patch(
        "homeassistant.components.lg_soundbar.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "name",
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 0000,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "name"
    assert result2["data"] == {
        CONF_NAME: "name",
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 0000,
        CONF_UNIQUE_ID: "uuid",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "homeassistant.components.lg_soundbar.config_flow.LGSoundbarConfigFlow.test_connect",
        side_effect=ConnectionError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "name",
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 0000,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_already_configured(hass):
    """Test we handle already configured error."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "name",
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 0000,
        },
        unique_id="uuid",
    )
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "homeassistant.components.lg_soundbar.config_flow.LGSoundbarConfigFlow.test_connect",
        return_value="uuid",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "name",
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 0000,
            },
        )

    assert result2["type"] == "abort"
    assert result2["reason"] == "already_configured"
