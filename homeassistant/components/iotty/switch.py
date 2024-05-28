"""Implement a iotty Light Switch Device."""

from __future__ import annotations

import logging
from typing import Any

from iottycloud.device import Device
from iottycloud.lightswitch import LightSwitch
from iottycloud.verbs import LS_DEVICE_TYPE_UID

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import IottyProxy
from .const import DOMAIN, KNOWN_DEVICES
from .coordinator import IottyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Activate the iotty LightSwitch component."""
    _LOGGER.debug("Setup SWITCH entry id is %s", config_entry.entry_id)

    hass_data = hass.data[DOMAIN]

    coordinator: IottyDataUpdateCoordinator = hass_data[config_entry.entry_id]

    entities = [
        IottyLightSwitch(
            coordinator=coordinator, iotty_cloud=coordinator.iotty, iotty_device=d
        )
        for d in coordinator.data.devices
        if d.device_type == LS_DEVICE_TYPE_UID
    ]
    _LOGGER.debug("Found %d LightSwitches", len(entities))

    async_add_entities(entities)

    @callback
    def async_update_data():
        """Handle updated data from the API endpoint."""
        if not coordinator.last_update_success:
            return

        devices = coordinator.data.devices
        entities = []
        known_devices: set = hass.data[DOMAIN][KNOWN_DEVICES]

        # Add entities for devices which we've not yet seen
        for device in devices:
            if device in known_devices:
                continue

            entities.extend(
                [
                    IottyLightSwitch(
                        coordinator=coordinator,
                        iotty_cloud=coordinator.iotty,
                        iotty_device=d,
                    )
                    for d in coordinator.data.devices
                    if d.device_type == LS_DEVICE_TYPE_UID
                    and d.device_id == device.device_id
                ]
            )
            known_devices.add(device)

        async_add_entities(entities)

        return devices

    # Add a subscriber to the coordinator to discover new devices
    coordinator.async_add_listener(async_update_data)


class IottyLightSwitch(SwitchEntity, CoordinatorEntity[Device]):
    """Haas entity class for iotty LightSwitch."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH
    _iotty_cloud: IottyProxy
    _iotty_device: LightSwitch

    def __init__(
        self,
        coordinator: IottyDataUpdateCoordinator,
        iotty_cloud: IottyProxy,
        iotty_device: LightSwitch,
    ) -> None:
        """Initialize the LightSwitch device."""
        super().__init__(coordinator=coordinator)

        _LOGGER.debug(
            "Creating new SWITCH (%s) %s",
            iotty_device.device_type,
            iotty_device.device_id,
        )

        self._iotty_cloud = iotty_cloud
        self._iotty_device = iotty_device
        self._attr_unique_id = iotty_device.device_id

    @property
    def device_id(self) -> str:
        """Get the ID of this iotty Device."""
        return self._iotty_device.device_id

    @property
    def is_on(self) -> bool:
        """Return true if the LightSwitch is on."""
        _LOGGER.debug(
            "Retrieve device status for %s ? %s",
            self._iotty_device.device_id,
            self._iotty_device.is_on,
        )
        return self._iotty_device.is_on

    @property
    def name(self) -> str:
        """Get the name of this iotty Device."""
        return self._iotty_device.name

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the LightSwitch on."""
        _LOGGER.debug("[%s] Turning on", self._iotty_device.device_id)
        await self._iotty_cloud.command(
            self._iotty_device.device_id, self._iotty_device.cmd_turn_on()
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the LightSwitch off."""
        _LOGGER.debug("[%s] Turning off", self._iotty_device.device_id)
        await self._iotty_cloud.command(
            self._iotty_device.device_id, self._iotty_device.cmd_turn_off()
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            device: LightSwitch = next(
                device
                for device in self.coordinator.data.devices
                if device.device_id == self._iotty_device.device_id
            )
            self._iotty_device.is_on = device.is_on
            self.async_write_ha_state()
        except StopIteration:
            _LOGGER.debug(
                "Device with id [%s] is no longer handled by iotty, please remove it from hass",
                self._iotty_device.device_id,
            )
