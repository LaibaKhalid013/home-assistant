"""Test the RKI Covid numbers integration config flow."""
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.rki_covid.const import DOMAIN
from homeassistant.core import HomeAssistant
from unittest.mock import patch
from unittest.mock import AsyncMock
from tests.common import MockConfigEntry

from homeassistant.components.rki_covid.coordinator import RkiCovidDataUpdateCoordinator
from rki_covid_parser.parser import RkiCovidParser
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from tests.components.rki_covid import MOCK_DISTRICTS, MOCK_STATES, MOCK_COUNTRY


async def test_successful_config_flow_with_district(hass: HomeAssistant) -> None:
    """Test a successful config flow with mock data."""
    coordinator = RkiCovidDataUpdateCoordinator(hass)
    coordinator.parser = RkiCovidParser(async_get_clientsession(hass))
    coordinator.parser.load_data = AsyncMock(return_value=None)
    coordinator.parser.districts = MOCK_DISTRICTS
    coordinator.parser.states = MOCK_STATES
    coordinator.parser.country = MOCK_COUNTRY
    with patch(
        "homeassistant.components.rki_covid.coordinator.RkiCovidDataUpdateCoordinator",
        return_value=coordinator,
    ):
        # Initialize a config flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Check that the config flow shows the user form
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"

        # Enter data into the config flow
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"county": "SK Amberg"},
        )

        # Validate the result
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "SK Amberg"
        assert result["result"]


async def test_successful_config_flow_with_country(hass: HomeAssistant) -> None:
    """Test a successful config flow with mock data."""
    coordinator = RkiCovidDataUpdateCoordinator(hass)
    coordinator.parser = RkiCovidParser(async_get_clientsession(hass))
    coordinator.parser.load_data = AsyncMock(return_value=None)
    coordinator.parser.districts = MOCK_DISTRICTS
    coordinator.parser.states = MOCK_STATES
    coordinator.parser.country = MOCK_COUNTRY
    with patch(
        "homeassistant.components.rki_covid.coordinator.RkiCovidDataUpdateCoordinator",
        return_value=coordinator,
    ):
        # Initialize a config flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Check that the config flow shows the user form
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"

        # Enter data into the config flow
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"county": "BL Bayern"},
        )

        # Validate the result
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "BL Bayern"
        assert result["result"]


async def test_successful_form(hass: HomeAssistant) -> None:
    """Test a successful form with mock data."""
    coordinator = RkiCovidDataUpdateCoordinator(hass)
    coordinator.parser = RkiCovidParser(async_get_clientsession(hass))
    coordinator.parser.load_data = AsyncMock(return_value=None)
    coordinator.parser.districts = MOCK_DISTRICTS
    coordinator.parser.states = MOCK_STATES
    coordinator.parser.country = MOCK_COUNTRY
    with patch(
        "homeassistant.components.rki_covid.coordinator.RkiCovidDataUpdateCoordinator",
        return_value=coordinator,
    ):
        # Initialize a config flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Check that the config flow
        assert result["type"] == "form"
        assert result["errors"] == {}

        # Enter data into the config flow
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"county": "BL Bayern"},
        )

        # Validate the result
        assert result2["type"] == "create_entry"
        assert result2["title"] == "BL Bayern"
        assert result2["data"] == {"county": "BL Bayern"}
        await hass.async_block_till_done()


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unload configuration."""
    coordinator = RkiCovidDataUpdateCoordinator(hass)
    coordinator.parser = RkiCovidParser(async_get_clientsession(hass))
    coordinator.parser.load_data = AsyncMock(return_value=None)
    coordinator.parser.districts = MOCK_DISTRICTS
    coordinator.parser.states = MOCK_STATES
    coordinator.parser.country = MOCK_COUNTRY
    with patch(
        "homeassistant.components.rki_covid.coordinator.RkiCovidDataUpdateCoordinator",
        return_value=coordinator,
    ):

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="test entry",
            unique_id="0123456",
            data={"county": "SK Amberg"},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_unload(entry.entry_id)
