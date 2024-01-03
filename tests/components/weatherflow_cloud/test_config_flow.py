"""Test the WeatherflowCloud config flow."""
import pytest

from homeassistant import config_entries
from homeassistant.components.weatherflow_cloud.const import DOMAIN
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_config(hass: HomeAssistant, mock_get_stations) -> None:
    """Test the config flow for the ideal case."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_TOKEN: "string",
        },
    )

    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_config_flow_abort(hass: HomeAssistant, mock_get_stations) -> None:
    """Test an abort case."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_TOKEN: "same_same",
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_TOKEN: "same_same",
        },
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "mock_fixture, expected_error",  # noqa: PT006
    [
        ("mock_get_stations_500_error", "cannot_connect"),
        ("mock_get_stations_401_error", "invalid_api_key"),
    ],
)
async def test_config_errors(
    hass: HomeAssistant, request, expected_error, mock_fixture, mock_get_stations
) -> None:
    """Test the config flow for various error scenarios."""
    mock_get_stations = request.getfixturevalue(mock_fixture)
    with mock_get_stations:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "string"},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": expected_error}
