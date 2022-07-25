"""Support for IntelliFire Binary Sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from intellifire4py import IntellifirePollData

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntellifireDataUpdateCoordinator
from .const import DOMAIN
from .entity import IntellifireEntity


@dataclass
class IntellifireBinarySensorRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[IntellifirePollData], bool]


@dataclass
class IntellifireBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntellifireBinarySensorRequiredKeysMixin
):
    """Describes a binary sensor entity."""


INTELLIFIRE_BINARY_SENSORS: tuple[IntellifireBinarySensorEntityDescription, ...] = (
    IntellifireBinarySensorEntityDescription(
        key="on_off",  # This is the sensor name
        name="Flame",  # This is the human readable name
        has_entity_name=True,
        icon="mdi:fire",
        value_fn=lambda data: data.is_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="timer_on",
        name="Timer on",
        has_entity_name=True,
        icon="mdi:camera-timer",
        value_fn=lambda data: data.timer_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="pilot_light_on",
        name="Pilot light on",
        has_entity_name=True,
        icon="mdi:fire-alert",
        value_fn=lambda data: data.pilot_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="thermostat_on",
        name="Thermostat on",
        has_entity_name=True,
        icon="mdi:home-thermometer-outline",
        value_fn=lambda data: data.thermostat_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_pilot_flame",
        name="Pilot flame error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_pilot_flame,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_flame",
        name="Flame error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_flame,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_fan_delay",
        name="Fan delay error",
        has_entity_name=True,
        icon="mdi:fan-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_fan_delay,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_maintenance",
        name="Maintenance error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_maintenance,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_disabled",
        name="Disabled error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_disabled,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_fan",
        name="Fan error",
        has_entity_name=True,
        icon="mdi:fan-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_fan,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_lights",
        name="Lights error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_lights,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_accessory",
        name="Accessory error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_accessory,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_soft_lock_out",
        name="Soft lock out error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_soft_lock_out,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_ecm_offline",
        name="Ecm offline error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_ecm_offline,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_offline",
        name="Offline error",
        has_entity_name=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_offline,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a IntelliFire On/Off Sensor."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntellifireBinarySensor(coordinator=coordinator, description=description)
        for description in INTELLIFIRE_BINARY_SENSORS
    )


class IntellifireBinarySensor(IntellifireEntity, BinarySensorEntity):
    """Extends IntellifireEntity with Binary Sensor specific logic."""

    entity_description: IntellifireBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Use this to get the correct value."""
        return self.entity_description.value_fn(self.coordinator.read_api.data)
