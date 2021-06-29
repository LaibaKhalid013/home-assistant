"""Support for Modern Forms Binary Sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ModernFormsDataUpdateCoordinator, ModernFormsDeviceEntity
from .const import CLEAR_TIMER, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Modern Forms binary sensors."""
    coordinator: ModernFormsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensors: list[ModernFormsBinarySensor] = [
        ModernFormsFanSleepTimerActive(entry.entry_id, coordinator),
    ]

    # Only setup light sleep timer sensor if light unit installed
    if coordinator.data.info.light_type:
        binary_sensors.append(
            ModernFormsLightSleepTimerActive(entry.entry_id, coordinator)
        )

    async_add_entities(binary_sensors)


class ModernFormsBinarySensor(ModernFormsDeviceEntity, BinarySensorEntity):
    """Defines a Modern Forms binary sensor."""

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

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return f"{self.coordinator.data.info.mac_address}_{self._key}"


class ModernFormsLightSleepTimerActive(ModernFormsBinarySensor):
    """Defines a Modern Forms Light Sleep Timer Active sensor."""

    def __init__(
        self, entry_id: str, coordinator: ModernFormsDataUpdateCoordinator
    ) -> None:
        """Initialize Modern Forms Light Sleep Timer Active sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:av-timer",
            key="light_sleep_timer_active",
            name=f"{coordinator.data.info.device_name} Light Sleep Timer Active",
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the timer."""
        return not (
            self.coordinator.data.state.light_sleep_timer == CLEAR_TIMER
            or (
                dt_util.utc_from_timestamp(
                    self.coordinator.data.state.light_sleep_timer
                )
                - dt_util.utcnow()
            ).total_seconds()
            < 0
        )


class ModernFormsFanSleepTimerActive(ModernFormsBinarySensor):
    """Defines a Modern Forms Fan Sleep Timer Active sensor."""

    def __init__(
        self, entry_id: str, coordinator: ModernFormsDataUpdateCoordinator
    ) -> None:
        """Initialize Modern Forms Fan Sleep Timer Active sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:av-timer",
            key="fan_sleep_timer_active",
            name=f"{coordinator.data.info.device_name} Fan Sleep Timer Active",
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the timer."""
        return not (
            self.coordinator.data.state.fan_sleep_timer == CLEAR_TIMER
            or (
                dt_util.utc_from_timestamp(self.coordinator.data.state.fan_sleep_timer)
                - dt_util.utcnow()
            ).total_seconds()
            < 0
        )
