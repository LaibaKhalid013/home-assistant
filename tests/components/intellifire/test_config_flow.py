"""Test the Intellifire config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.intellifire.const import DOMAIN
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
        "homeassistant.components.intellifire.config_flow.validate_input",
        return_value={"title": "Living Room Fireplace", "type": "Fireplace"},
    ), patch(
        "homeassistant.components.intellifire.async_setup_entry", return_value=True
    ) as mock_setup_entry:

        print("mock_setup_entry", mock_setup_entry)
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "name": "Fuego",
            },
        )
        await hass.async_block_till_done()

    print(result2)

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Living Room Fireplace"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "name": "Fuego",
    }
    assert len(mock_setup_entry.mock_calls) == 2


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "intellifire4py.IntellifireAsync.poll",
        side_effect=ConnectionError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "name": "Fuego",
            },
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}
