"""Test the VARTA Storage config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.varta_storage.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.varta_storage.config_flow.VartaHub.test_connection",
        return_value=True,
    ), patch(
        "homeassistant.components.varta_storage.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.0.2.3", "port": 502},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    # assert result2["title"] == "VARTA Storage"
    assert result2["data"] == {"host": "10.0.2.3", "port": 502}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("vartastorage.client.Client.connect", return_value=False), patch(
        "vartastorage.client.Client.get_serial", return_value=""
    ):
        result1 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.0.2.3", "port": 502},
        )
    assert result1["type"] == RESULT_TYPE_FORM
    assert result1["errors"] == {"base": "cannot_connect"}
    with patch(
        "vartastorage.vartastorage.VartaStorage.get_serial",
        side_effect=ValueError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.0.2.3", "port": 502},
        )
    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}
    with patch(
        "homeassistant.components.varta_storage.config_flow.VartaHub.test_connection",
        return_value=False,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.0.2.3", "port": 502},
        )
    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {"base": "cannot_connect"}
    with patch(
        "homeassistant.components.varta_storage.config_flow.VartaHub.test_connection",
        side_effect=TypeError,
    ):
        result4 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.0.2.3", "port": 502},
        )
    assert result4["type"] == RESULT_TYPE_FORM
    assert result4["errors"] == {"base": "unknown"}
