"""The AccuWeather coordinator."""

from __future__ import annotations

from asyncio import timeout
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from accuweather import AccuWeather, ApiError, InvalidApiKeyError, RequestsExceededError
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    MANUFACTURER,
    UPDATE_INTERVAL_DAILY_FORECAST,
    UPDATE_INTERVAL_OBSERVATION,
)

EXCEPTIONS = (ApiError, ClientConnectorError, InvalidApiKeyError, RequestsExceededError)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AccuWeatherData:
    """Data for AccuWeather integration."""

    coordinator_observation: AccuWeatherObservationDataUpdateCoordinator
    coordinator_daily_forecast: AccuWeatherDailyForecastDataUpdateCoordinator


type AccuWeatherConfigEntry = ConfigEntry[AccuWeatherData]


class AccuWeatherObservationDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, Any]]
):
    """Class to manage fetching AccuWeather data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: AccuWeatherConfigEntry,
        accuweather: AccuWeather,
    ) -> None:
        """Initialize."""
        self.accuweather = accuweather
        self.location_key = accuweather.location_key

        if TYPE_CHECKING:
            assert self.location_key is not None
        name: str = config_entry.data[CONF_NAME]
        self.device_info = _get_device_info(self.location_key, name)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{name} (observation)",
            update_interval=UPDATE_INTERVAL_OBSERVATION,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with timeout(10):
                result = await self.accuweather.async_get_current_conditions()
        except EXCEPTIONS as error:
            raise UpdateFailed(error) from error

        _LOGGER.debug("Requests remaining: %d", self.accuweather.requests_remaining)

        return result


class AccuWeatherDailyForecastDataUpdateCoordinator(
    TimestampDataUpdateCoordinator[list[dict[str, Any]]]
):
    """Class to manage fetching AccuWeather data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: AccuWeatherConfigEntry,
        accuweather: AccuWeather,
    ) -> None:
        """Initialize."""
        self.accuweather = accuweather
        self.location_key = accuweather.location_key

        if TYPE_CHECKING:
            assert self.location_key is not None

        name: str = config_entry.data[CONF_NAME]
        self.device_info = _get_device_info(self.location_key, name)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{name} (daily forecast)",
            update_interval=UPDATE_INTERVAL_DAILY_FORECAST,
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Update data via library."""
        try:
            async with timeout(10):
                result = await self.accuweather.async_get_daily_forecast()
        except EXCEPTIONS as error:
            raise UpdateFailed(error) from error

        _LOGGER.debug("Requests remaining: %d", self.accuweather.requests_remaining)

        return result


def _get_device_info(location_key: str, name: str) -> DeviceInfo:
    """Get device info."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, location_key)},
        manufacturer=MANUFACTURER,
        name=name,
        # You don't need to provide specific details for the URL,
        # so passing in _ characters is fine if the location key
        # is correct
        configuration_url=(
            "http://accuweather.com/en/"
            f"_/_/{location_key}/weather-forecast/{location_key}/"
        ),
    )
