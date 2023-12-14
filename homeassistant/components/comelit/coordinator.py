"""Support for Comelit."""
from datetime import timedelta
from typing import Any

from aiocomelit import (
    ComeliteSerialBridgeApi,
    ComelitSerialBridgeObject,
    ComelitVedoApi,
    ComelitVedoAreaObject,
    ComelitVedoZoneObject,
    exceptions,
)
from aiocomelit.const import BRIDGE, VEDO

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import _LOGGER, DOMAIN


class ComelitBaseCoordinator(DataUpdateCoordinator):
    """Base coordinator for Comelit Devices."""

    config_entry: ConfigEntry
    api: Any

    def __init__(
        self, hass: HomeAssistant, device: str, hw_version: str, host: str
    ) -> None:
        """Initialize the scanner."""

        self._device = device
        self._hw_version = hw_version
        self._host = host

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{host}-coordinator",
            update_interval=timedelta(seconds=5),
        )
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            model=device,
            name=f"{device} ({self._host})",
            manufacturer="Comelit",
            hw_version=self._hw_version,
        )

    def platform_device_info(
        self,
        object_class: ComelitVedoAreaObject
        | ComelitVedoZoneObject
        | ComelitSerialBridgeObject,
    ) -> dr.DeviceInfo:
        """Set platform device info."""

        if type(object_class) == ComelitSerialBridgeObject:
            object_type = object_class.type
        elif type(object_class) == ComelitVedoAreaObject:
            object_type = "area"
        else:
            object_type = "zone"

        return dr.DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.config_entry.entry_id}-{object_type}-{object_class.index}",
                )
            },
            via_device=(DOMAIN, self.config_entry.entry_id),
            name=object_class.name,
            model=f"{self._device} {object_type}",
            manufacturer="Comelit",
            hw_version=self._hw_version,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update device data."""
        _LOGGER.debug("Polling Comelit %s host: %s", self._device, self._host)
        try:
            await self.api.login()
            if type(self.api) == ComelitVedoApi:
                return await self.api.get_all_areas_and_zones()

            if type(self.api) == ComeliteSerialBridgeApi:
                return await self.api.get_all_devices()

        except exceptions.CannotConnect as err:
            _LOGGER.warning("Connection error for %s", self._host)
            await self.api.close()
            raise UpdateFailed(f"Error fetching data: {repr(err)}") from err
        except exceptions.CannotAuthenticate:
            raise ConfigEntryAuthFailed

        return {}


class ComelitSerialBridge(ComelitBaseCoordinator):
    """Queries Comelit Serial Bridge."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, pin: int) -> None:
        """Initialize the scanner."""
        self.api = ComeliteSerialBridgeApi(host, port, pin)
        super().__init__(hass, BRIDGE, "20003101", host)


class ComelitVedoSystem(ComelitBaseCoordinator):
    """Queries Comelit VEDO system."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, pin: int) -> None:
        """Initialize the scanner."""
        self.api = ComelitVedoApi(host, port, pin)
        super().__init__(hass, VEDO, "VEDO IP", host)
