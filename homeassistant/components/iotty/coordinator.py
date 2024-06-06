"""DataUpdateCoordinator for iotty."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from iottycloud.device import Device
from iottycloud.verbs import RESULT, STATUS

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import api
from .const import DOMAIN, LOGGER

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


@dataclass
class IottyData:
    """iotty data stored in the DataUpdateCoordinator."""

    devices: list[Device]


class IottyDataUpdateCoordinator(DataUpdateCoordinator[IottyData]):
    """Class to manage fetching Iotty data."""

    config_entry: ConfigEntry
    _entities: dict[str, Entity]
    _devices: list[Device]

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, session: OAuth2Session
    ) -> None:
        """Initialize the coordinator."""
        _LOGGER.debug("Initializing iotty data update coordinator")

        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=UPDATE_INTERVAL,
        )

        self.config_entry = entry
        self._entities = {}
        self._devices = []
        self.iotty = api.IottyProxy(
            hass, aiohttp_client.async_get_clientsession(hass), session
        )

    def set_entity(self, device_id: str, entity: Entity) -> None:
        """Store iotty device within Hass entities."""
        _LOGGER.debug("Storing device '%s' in entities", device_id)
        self._entities[device_id] = entity

    async def async_config_entry_first_refresh(self) -> None:
        """Override the first refresh to also fetch iotty devices list."""
        _LOGGER.debug("Fetching devices list from iottyCloud")
        self._devices = await self.iotty.get_devices()
        _LOGGER.debug("There are %d devices", len(self._devices))

        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> IottyData:
        """Fetch data from iottyCloud device."""
        _LOGGER.debug("Fetching devices status from iottyCloud")

        self._devices = await self.iotty.get_devices()

        for device in self._devices:
            res = await self.iotty.get_status(device.device_id)
            json = res.get(RESULT, {})
            if (
                not isinstance(res, dict)
                or RESULT not in res
                or not isinstance(json := res[RESULT], dict)
                or not (status := json.get(STATUS))
            ):
                _LOGGER.warning("Unable to read status for device %s", device.device_id)
            else:
                _LOGGER.debug(
                    "Retrieved status: '%s' for device %s", status, device.device_id
                )
                device.update_status(status)

        return IottyData(self._devices)
