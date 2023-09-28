"""Entity for Refoss."""

from __future__ import annotations

from refoss_ha.controller.device import BaseDevice

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class RefossEntity(
    Entity,
):
    """Entity for refoss."""

    _attr_has_entity_name = True

    def __init__(self, device: BaseDevice, channel: int) -> None:
        """__init__."""
        self._attr_unique_id = f"refoss_{device.uuid}_{channel}"
        if channel == 0:
            self._attr_name = None
        else:
            self._attr_name = str(channel)
        self.device = device
        self.channel = channel
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.uuid)},
            manufacturer="refoss",
            model=device.device_type,
            name=device.dev_name,
            sw_version=device.fmware_version,
            hw_version=device.hdware_version,
        )

    @property
    def available(self) -> bool:
        """Return True if the device is online."""
        return self.device.online

    async def async_device_update(self, warning: bool = True) -> None:
        """Async update device status."""
        await self.device.async_handle_update(self.channel)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        self.device.register_push_notification_handler_coroutine(
            self._async_push_notification_received
        )

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity is remove from hass."""
        self.device.unregister_push_notification_handler_coroutine(
            self._async_push_notification_received
        )

    async def _async_push_notification_received(
        self, namespace: str, data: dict, uuid: str
    ) -> None:
        """Synchronize the status of device push."""
        await self.device.async_update_push_state(
            namespace=namespace, data=data, uuid=uuid
        )
        self.async_write_ha_state()
