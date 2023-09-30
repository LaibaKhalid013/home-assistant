"""The Renson integration."""
from __future__ import annotations

from dataclasses import dataclass

from renson_endura_delta.renson import Level, RensonVentilation

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    SET_BREEZE_SCHEMA,
    SET_DAY_NIGHT_TIME_SCHEMA,
    SET_POLLUTION_SETTINGS_SCHEMA,
    SET_TIMER_LEVEL_SCHEMA,
)
from .coordinator import RensonCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SENSOR,
]


@dataclass
class RensonData:
    """Renson data class."""

    api: RensonVentilation
    coordinator: RensonCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renson from a config entry."""

    api = RensonVentilation(entry.data[CONF_HOST])
    coordinator = RensonCoordinator("Renson", hass, api)

    if not await hass.async_add_executor_job(api.connect):
        raise ConfigEntryNotReady("Cannot connect to Renson device")

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = RensonData(
        api,
        coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    setup_hass_services(hass, api)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def setup_hass_services(hass: HomeAssistant, renson_api: RensonVentilation) -> None:
    """Set up the Renson platforms."""

    async def set_timer_level(call: ServiceCall) -> None:
        """Set timer level."""
        level_string = call.data["timer_level"]
        time = call.data["time"]
        level = Level[str(level_string).upper()]

        await hass.async_add_executor_job(renson_api.set_timer_level, level, time)

    async def set_breeze(call: ServiceCall) -> None:
        """Configure breeze feature."""
        level = call.data["breeze_level"]
        temperature = call.data["temperature"]
        activated = call.data["activate"]

        await hass.async_add_executor_job(
            renson_api.set_breeze, level, temperature, activated
        )

    async def set_day_night_time(call: ServiceCall) -> None:
        """Configure day night times."""
        day = call.data["day"]
        night = call.data["night"]

        await hass.async_add_executor_job(renson_api.set_time, day, night)

    async def set_pollution_settings(call: ServiceCall) -> None:
        """Configure pollutions settings."""
        day = call.data["day_pollution_level"]
        night = call.data["night_pollution_level"]
        humidity_control = call.data.get("humidity_control")
        airquality_control = call.data.get("airquality_control")
        co2_control = call.data.get("co2_control")
        co2_threshold = call.data.get("co2_threshold")
        co2_hysteresis = call.data.get("co2_hysteresis")

        await renson_api.set_pollution(
            day,
            night,
            humidity_control,
            airquality_control,
            co2_control,
            co2_threshold,
            co2_hysteresis,
        )

    hass.services.async_register(DOMAIN, "set_breeze", set_breeze, SET_BREEZE_SCHEMA)
    hass.services.async_register(
        DOMAIN, "set_day_night_time", set_day_night_time, SET_DAY_NIGHT_TIME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "set_pollution_settings",
        set_pollution_settings,
        SET_POLLUTION_SETTINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "set_timer_level", set_timer_level, SET_TIMER_LEVEL_SCHEMA
    )
