"""Support for D-Link Power Plug Switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DLinkConfigEntry
from .const import ATTR_TOTAL_CONSUMPTION
from .entity import DLinkEntity

SWITCH_TYPE = SwitchEntityDescription(
    key="switch",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the D-Link Power Plug switch."""
    async_add_entities([SmartPlugSwitch(entry, SWITCH_TYPE)], True)


class SmartPlugSwitch(DLinkEntity, SwitchEntity):
    """Representation of a D-Link Smart Plug switch."""

    _attr_name = None

    # Deprecated, can be removed in 2024.11
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the device."""
        try:
            temperature = self.hass.config.units.temperature(
                int(self.coordinator.data.temperature), UnitOfTemperature.CELSIUS
            )
        except ValueError:
            temperature = None

        try:
            total_consumption = float(self.coordinator.data.total_consumption)
        except ValueError:
            total_consumption = None

        return {
            ATTR_TOTAL_CONSUMPTION: total_consumption,
            ATTR_TEMPERATURE: temperature,
        }

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data.state == "ON"

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.smartplug.state = "ON"

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.coordinator.smartplug.state = "OFF"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.available
