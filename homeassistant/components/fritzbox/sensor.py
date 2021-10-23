"""Support for AVM FRITZ!SmartHome temperature sensor only devices."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final
from datetime import datetime

from pyfritzhome.fritzhomedevice import FritzhomeDevice
from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    ENERGY_KILO_WATT_HOUR,
    ENTITY_CATEGORY_DIAGNOSTIC,
    PERCENTAGE,
    POWER_WATT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FritzBoxEntity
from .const import CONF_COORDINATOR, DOMAIN as FRITZBOX_DOMAIN
from .model import FritzEntityDescriptionMixinBase


@dataclass
class FritzEntityDescriptionMixinSensor(FritzEntityDescriptionMixinBase):
    """Sensor description mixin for Fritz!Smarthome entities."""

    native_value: Callable[[FritzhomeDevice], float | int | None]


@dataclass
class FritzSensorEntityDescription(
    SensorEntityDescription, FritzEntityDescriptionMixinSensor
):
    """Description for Fritz!Smarthome sensor entities."""


SENSOR_TYPES: Final[tuple[FritzSensorEntityDescription, ...]] = (
    FritzSensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        suitable=lambda device: (
            device.has_temperature_sensor and not device.has_thermostat
        ),
        native_value=lambda device: device.temperature,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=DEVICE_CLASS_HUMIDITY,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.rel_humidity is not None,
        native_value=lambda device: device.rel_humidity,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=DEVICE_CLASS_BATTERY,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        suitable=lambda device: device.battery_level is not None,
        native_value=lambda device: device.battery_level,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="power_consumption",
        name="Power Consumption",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_powermeter,  # type: ignore[no-any-return]
        native_value=lambda device: device.power / 1000 if device.power else 0.0,
    ),
    FritzSensorEntityDescription(
        key="total_energy",
        name="Total Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        suitable=lambda device: device.has_powermeter,  # type: ignore[no-any-return]
        native_value=lambda device: device.energy / 1000 if device.energy else 0.0,
    ),
    # Thermostat Sensors
    FritzSensorEntityDescription(
        key="comfort_temperature",
        name="Comfort Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.comfort_temperature is not None,
        native_value=lambda device: device.comfort_temperature,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="eco_temperature",
        name="Eco Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.eco_temperature is not None,
        native_value=lambda device: device.eco_temperature,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="nextchange_temperature",
        name="Next Scheduled Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.nextchange_temperature is not None,
        native_value=lambda device: device.comfort_temperature,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="nextchange_time",
        name="Next Scheduled Change Time",
        device_class=DEVICE_CLASS_TIMESTAMP,
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.nextchange_endperiod is not None,
        native_value=lambda device: datetime.fromtimestamp(device.nextchange_endperiod).isoformat(),  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="nextchange_preset",
        name="Next Scheduled Preset",
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.nextchange_temperature is not None,
        native_value=lambda device: PRESET_ECO if device.nextchange_temperature == device.eco_temperature else PRESET_COMFORT,  # type: ignore[no-any-return]
    ),
    FritzSensorEntityDescription(
        key="scheduled_preset",
        name="Current Scheduled Preset",
        state_class=STATE_CLASS_MEASUREMENT,
        suitable=lambda device: device.has_thermostat
        and device.nextchange_temperature is not None,
        native_value=lambda device: PRESET_COMFORT if device.nextchange_temperature == device.eco_temperature else PRESET_ECO,  # type: ignore[no-any-return]
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the FRITZ!SmartHome sensor from ConfigEntry."""
    coordinator = hass.data[FRITZBOX_DOMAIN][entry.entry_id][CONF_COORDINATOR]

    async_add_entities(
        [
            FritzBoxSensor(coordinator, ain, description)
            for ain, device in coordinator.data.items()
            for description in SENSOR_TYPES
            if description.suitable(device)
        ]
    )


class FritzBoxSensor(FritzBoxEntity, SensorEntity):
    """The entity class for FRITZ!SmartHome sensors."""

    entity_description: FritzSensorEntityDescription

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the sensor."""
        return self.entity_description.native_value(self.device)
