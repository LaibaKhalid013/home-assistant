"""Support for Big Ass Fans SenseME selects."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from aiosenseme import SensemeFan
from aiosenseme.device import AUTOCOMFORTS, SensemeDevice

from homeassistant import config_entries
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SensemeEntity


@dataclass
class SenseMESelectEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[SensemeFan], str]
    set_fn: Callable[[SensemeFan, str], None]


@dataclass
class SenseMESelectEntityDescription(
    SelectEntityDescription, SenseMESelectEntityDescriptionMixin
):
    """Describes SenseME select entity."""


def _set_auto_comfort_mode(device: SensemeDevice, value: str) -> None:
    device.fan_autocomfort = value


FAN_SELECTS = [
    SenseMESelectEntityDescription(
        key="auto_comfort",
        name="Auto Comfort",
        value_fn=lambda device: cast(str, device.fan_autocomfort),
        set_fn=_set_auto_comfort_mode,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SenseME fan selects."""
    device = hass.data[DOMAIN][entry.entry_id]
    if device.is_fan:
        async_add_entities(
            HASensemeSelect(device, description) for description in FAN_SELECTS
        )


class HASensemeSelect(SensemeEntity, SelectEntity):
    """SenseME switch component."""

    entity_description: SenseMESelectEntityDescription

    def __init__(
        self, device: SensemeFan, description: SenseMESelectEntityDescription
    ) -> None:
        """Initialize the entity."""
        self.entity_description = description
        super().__init__(device, f"{device.name} {description.name}")
        self._attr_unique_id = f"{self._device.uuid}-{description.key}"
        self._attr_options = AUTOCOMFORTS

    @property
    def current_option(self) -> str:
        """Return the current value."""
        return self.entity_description.value_fn(self._device)

    async def async_select_option(self, option: str) -> None:
        """Set the option."""
        return self.entity_description.set_fn(self._device, option)
