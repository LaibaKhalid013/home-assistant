"""Support for KNX/IP switches."""
from typing import Any, Callable, Optional

from xknx.devices import Switch as XknxSwitch

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from . import DOMAIN
from .knx_entity import KnxEntity


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up switch(es) for KNX platform."""
    entities = []
    for device in hass.data[DOMAIN].xknx.devices:
        if isinstance(device, XknxSwitch):
            entities.append(KNXSwitch(device))
    async_add_entities(entities)


class KNXSwitch(KnxEntity, SwitchEntity):
    """Representation of a KNX switch."""

    def __init__(self, device: XknxSwitch):
        """Initialize of KNX switch."""
        self._device: XknxSwitch
        super().__init__(device)

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return bool(self._device.state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self._device.set_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self._device.set_off()
