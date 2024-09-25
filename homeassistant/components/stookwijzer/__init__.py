"""The Stookwijzer integration."""

from __future__ import annotations

import logging

from stookwijzer import Stookwijzer

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import StookwijzerCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type StookwijzerConfigEntry = ConfigEntry[StookwijzerCoordinator]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        session = async_get_clientsession(hass)
        x, y = await Stookwijzer.async_transform_coordinates(
            session,
            config_entry.data[CONF_LOCATION][CONF_LATITUDE],
            config_entry.data[CONF_LOCATION][CONF_LONGITUDE],
        )

        if not x or not y:
            _LOGGER.error(
                "Migration to version %s not successful", config_entry.version
            )
            return False
        hass.config_entries.async_update_entry(
            config_entry, version=2, data={CONF_LATITUDE: x, CONF_LONGITUDE: y}
        )

        _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stookwijzer from a config entry."""
    client = Stookwijzer(
        async_get_clientsession(hass),
        entry.data[CONF_LATITUDE],
        entry.data[CONF_LONGITUDE],
    )
    coordinator = StookwijzerCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Stookwijzer config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
