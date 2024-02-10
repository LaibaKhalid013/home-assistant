"""Button entities for the Motionblinds BLE integration."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from motionblindsble.device import MotionDevice

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_CONNECT,
    ATTR_DISCONNECT,
    ATTR_FAVORITE,
    CONF_BLIND_TYPE,
    CONF_MAC_CODE,
    DOMAIN,
    ICON_CONNECT,
    ICON_DISCONNECT,
    ICON_FAVORITE,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True)
class CommandButtonEntityDescription(ButtonEntityDescription):
    """Entity description of a button entity that executes a command upon being pressed."""

    command_callback: Callable[[MotionDevice], Coroutine[Any, Any, None]] | None = None


async def command_connect(device: MotionDevice) -> None:
    """Connect when the connect button is pressed."""
    await device.connect()


async def command_disconnect(device: MotionDevice) -> None:
    """Disconnect when the disconnect button is pressed."""
    await device.disconnect()


async def command_favorite(device: MotionDevice) -> None:
    """Go to the favorite position when the favorite button is pressed."""
    await device.favorite()


BUTTON_TYPES: dict[str, CommandButtonEntityDescription] = {
    ATTR_CONNECT: CommandButtonEntityDescription(
        key=ATTR_CONNECT,
        translation_key=ATTR_CONNECT,
        icon=ICON_CONNECT,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
        command_callback=command_connect,
    ),
    ATTR_DISCONNECT: CommandButtonEntityDescription(
        key=ATTR_DISCONNECT,
        translation_key=ATTR_DISCONNECT,
        icon=ICON_DISCONNECT,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
        command_callback=command_disconnect,
    ),
    ATTR_FAVORITE: CommandButtonEntityDescription(
        key=ATTR_FAVORITE,
        translation_key=ATTR_FAVORITE,
        icon=ICON_FAVORITE,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
        command_callback=command_favorite,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up buttons based on a config entry."""

    device: MotionDevice = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            GenericCommandButton(device, entry, entity_description)
            for entity_description in BUTTON_TYPES.values()
        ]
    )


class GenericCommandButton(ButtonEntity):
    """Representation of a command button."""

    _device: MotionDevice
    entity_description: CommandButtonEntityDescription

    def __init__(
        self,
        device: MotionDevice,
        entry: ConfigEntry,
        entity_description: CommandButtonEntityDescription,
    ) -> None:
        """Initialize the command button."""
        _LOGGER.info(
            "(%s) Setting up %s button entity",
            entry.data[CONF_MAC_CODE],
            entity_description.key,
        )
        self._device: MotionDevice = device
        self.entity_description: CommandButtonEntityDescription = entity_description

        self._attr_unique_id: str = (
            f"{entry.data[CONF_ADDRESS]}_{entity_description.key}"
        )
        self._attr_device_info: DeviceInfo = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, entry.data[CONF_ADDRESS])},
            manufacturer=MANUFACTURER,
            model=entry.data[CONF_BLIND_TYPE],
            name=device.display_name,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        if callable(self.entity_description.command_callback):
            await self.entity_description.command_callback(self._device)
