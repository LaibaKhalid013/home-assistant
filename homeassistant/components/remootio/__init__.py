"""The Remootio integration."""
from __future__ import annotations

import logging

from aioremootio import ConnectionOptions, RemootioClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback

from .const import (
    ATTR_SERIAL_NUMBER,
    CONF_API_AUTH_KEY,
    CONF_API_SECRET_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
    EVENT_HANDLER_CALLBACK,
    REMOOTIO_CLIENT,
)
from .cover import RemootioCoverEvent
from .utils import create_client

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Remootio from a config entry."""

    _LOGGER.debug("Doing async_setup_entry. entry [%s]", entry.as_dict())

    @callback
    def handle_event(event: RemootioCoverEvent) -> None:
        _LOGGER.debug(
            "Firing event. EvenType [%s] RemootioCoverEntityId [%s] RemootioDeviceSerialNumber [%s]",
            event.type,
            event.entity_id,
            event.device_serial_number,
        )

        hass.bus.async_fire(
            event.type,
            {
                ATTR_ENTITY_ID: event.entity_id,
                ATTR_SERIAL_NUMBER: event.device_serial_number,
                ATTR_NAME: event.entity_name,
            },
        )

    connection_options: ConnectionOptions = ConnectionOptions(
        entry.data[CONF_HOST],
        entry.data[CONF_API_SECRET_KEY],
        entry.data[CONF_API_AUTH_KEY],
        False,
    )
    serial_number: str = entry.data[CONF_SERIAL_NUMBER]

    remootio_client: RemootioClient = await create_client(
        hass, connection_options, _LOGGER, serial_number
    )

    hass_data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    hass_data[REMOOTIO_CLIENT] = remootio_client
    hass_data[EVENT_HANDLER_CALLBACK] = handle_event

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.debug(
        "Doing async_unload_entry. entry [%s] hass.data[%s][%s] [%s]",
        entry.as_dict(),
        DOMAIN,
        entry.entry_id,
        hass.data.get(DOMAIN, {}).get(entry.entry_id, {}),
    )

    platforms_unloaded = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if platforms_unloaded and DOMAIN in hass.data:
        hass_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        if REMOOTIO_CLIENT in hass_data:
            remootio_client: RemootioClient = hass_data.pop(REMOOTIO_CLIENT, None)
            if remootio_client is not None:
                terminated: bool = await remootio_client.terminate()
                if terminated:
                    _LOGGER.debug(
                        "Remootio client successfully terminated. entry [%s]",
                        entry.as_dict(),
                    )

    return platforms_unloaded
