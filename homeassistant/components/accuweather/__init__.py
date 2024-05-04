"""The AccuWeather component."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from accuweather import AccuWeather

from homeassistant.components.sensor import DOMAIN as SENSOR_PLATFORM
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, UPDATE_INTERVAL_DAILY_FORECAST, UPDATE_INTERVAL_OBSERVATION
from .coordinator import (
    AccuWeatherDailyForecastDataUpdateCoordinator,
    AccuWeatherObservationDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.WEATHER]

AccuWeatherConfigEntry = ConfigEntry["AccuWeatherData"]


@dataclass
class AccuWeatherData:
    """Data for AccuWeather integration."""

    coordinator_observation: AccuWeatherObservationDataUpdateCoordinator
    coordinator_daily_forecast: AccuWeatherDailyForecastDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: AccuWeatherConfigEntry) -> bool:
    """Set up AccuWeather as config entry."""
    api_key: str = entry.data[CONF_API_KEY]
    name: str = entry.data[CONF_NAME]

    location_key = entry.unique_id

    _LOGGER.debug("Using location_key: %s", location_key)

    websession = async_get_clientsession(hass)
    accuweather = AccuWeather(api_key, websession, location_key=location_key)

    coordinator_observation = AccuWeatherObservationDataUpdateCoordinator(
        hass,
        accuweather,
        name,
        "observation",
        UPDATE_INTERVAL_OBSERVATION,
    )

    coordinator_daily_forecast = AccuWeatherDailyForecastDataUpdateCoordinator(
        hass,
        accuweather,
        name,
        "daily forecast",
        UPDATE_INTERVAL_DAILY_FORECAST,
    )

    await coordinator_observation.async_config_entry_first_refresh()
    await coordinator_daily_forecast.async_config_entry_first_refresh()

    entry.runtime_data = AccuWeatherData(
        coordinator_observation=coordinator_observation,
        coordinator_daily_forecast=coordinator_daily_forecast,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Remove ozone sensors from registry if they exist
    ent_reg = er.async_get(hass)
    for day in range(5):
        unique_id = f"{location_key}-ozone-{day}"
        if entity_id := ent_reg.async_get_entity_id(SENSOR_PLATFORM, DOMAIN, unique_id):
            _LOGGER.debug("Removing ozone sensor entity %s", entity_id)
            ent_reg.async_remove(entity_id)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AccuWeatherConfigEntry
) -> bool:
    """Unload a config entry."""
<<<<<<< HEAD
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
=======
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: AccuWeatherConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
>>>>>>> e0cb5f6801 (Use config_entry.runtime_data to store data)
