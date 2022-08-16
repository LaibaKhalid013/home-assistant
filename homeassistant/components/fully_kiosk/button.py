"""Fully Kiosk Browser button."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FullyKioskDataUpdateCoordinator
from .entity import FullyKioskEntity


@dataclass
class FullyButtonEntityDescription(ButtonEntityDescription):
    """Fully Kiosk Browser button description."""

    press_action: Callable | None = None


BUTTONS: tuple[FullyButtonEntityDescription, ...] = (
    FullyButtonEntityDescription(
        key="restartApp",
        name="Restart Browser",
        press_action=lambda fully: fully.restartApp(),
    ),
    FullyButtonEntityDescription(
        key="rebootDevice",
        name="Reboot Device",
        press_action=lambda fully: fully.rebootDevice(),
    ),
    FullyButtonEntityDescription(
        key="toForeground",
        name="Bring to Foreground",
        press_action=lambda fully: fully.toForeground(),
    ),
    FullyButtonEntityDescription(
        key="toBackground",
        name="Send to Background",
        press_action=lambda fully: fully.toBackground(),
    ),
    FullyButtonEntityDescription(
        key="loadStartUrl",
        name="Load Start URL",
        press_action=lambda fully: fully.loadStartUrl(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fully Kiosk Browser button entities."""
    coordinator: FullyKioskDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities(
        FullyButtonEntity(coordinator, description) for description in BUTTONS
    )


class FullyButtonEntity(FullyKioskEntity, ButtonEntity):
    """Representation of a Fully Kiosk Browser button."""

    def __init__(
        self,
        coordinator: FullyKioskDataUpdateCoordinator,
        description: FullyButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data['deviceID']}-{description.key}"

    async def async_press(self) -> None:
        """Set the value of the entity."""
        await self.entity_description.press_action(self.coordinator.fully)
        await self.coordinator.async_refresh()
