"""Support for Modern Forms switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (
    ModernFormsDataUpdateCoordinator,
    ModernFormsDeviceEntity,
    modernforms_exception_handler,
)
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Modern Forms switch based on a config entry."""
    coordinator: ModernFormsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        ModernFormsAwaySwitch(entry.entry_id, coordinator),
        ModernFormsAdaptiveLearningSwitch(entry.entry_id, coordinator),
        ModernFormsRebootSwitch(entry.entry_id, coordinator),
    ]
    async_add_entities(switches)


class ModernFormsSwitch(ModernFormsDeviceEntity, SwitchEntity):
    """Defines a Modern Forms switch."""

    def __init__(
        self,
        *,
        entry_id: str,
        coordinator: ModernFormsDataUpdateCoordinator,
        name: str,
        icon: str,
        key: str,
    ) -> None:
        """Initialize Modern Forms switch."""
        self._key = key
        super().__init__(
            entry_id=entry_id, coordinator=coordinator, name=name, icon=icon
        )
        self._attr_unique_id = f"{self.coordinator.data.info.mac_address}_{self._key}"


class ModernFormsAwaySwitch(ModernFormsSwitch):
    """Defines a Modern Forms Away mode switch."""

    def __init__(
        self, entry_id: str, coordinator: ModernFormsDataUpdateCoordinator
    ) -> None:
        """Initialize Modern Forms Away mode switch."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:airplane-takeoff",
            key="away_mode",
            name=f"{coordinator.data.info.device_name} Away Mode",
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return bool(self.coordinator.data.state.away_mode_enabled)

    @modernforms_exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Modern Forms Away mode switch."""
        await self.coordinator.modern_forms.away(away=False)

    @modernforms_exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Modern Forms Away mode switch."""
        await self.coordinator.modern_forms.away(away=True)


class ModernFormsAdaptiveLearningSwitch(ModernFormsSwitch):
    """Defines a Modern Forms Adaptive Learning switch."""

    def __init__(
        self, entry_id: str, coordinator: ModernFormsDataUpdateCoordinator
    ) -> None:
        """Initialize Modern Forms Adaptive Learning switch."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:school-outline",
            key="adaptive_learning",
            name=f"{coordinator.data.info.device_name} Adaptive Learning",
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return bool(self.coordinator.data.state.adaptive_learning_enabled)

    @modernforms_exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Modern Forms Adaptive Learning switch."""
        await self.coordinator.modern_forms.adaptive_learning(adaptive_learning=False)

    @modernforms_exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Modern Forms Adaptive Learning switch."""
        await self.coordinator.modern_forms.adaptive_learning(adaptive_learning=True)


class ModernFormsRebootSwitch(ModernFormsSwitch):
    """Defines a Modern Forms Reboot switch."""

    def __init__(
        self, entry_id: str, coordinator: ModernFormsDataUpdateCoordinator
    ) -> None:
        """Initialize Modern Forms Reboot switch."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:restart",
            key="reboot",
            name=f"{coordinator.data.info.device_name} Reboot",
        )

    @property
    def is_on(self) -> bool:
        """Return false as the switch will never be on."""
        return False

    @modernforms_exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Modern Forms reboot switch."""
        pass

    @modernforms_exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Modern Forms Reboot switch."""
        await self.coordinator.modern_forms.reboot()
