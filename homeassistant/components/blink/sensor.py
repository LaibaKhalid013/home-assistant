"""Support for Blink system camera sensors."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DEFAULT_BRAND, DOMAIN, TYPE_TEMPERATURE, TYPE_WIFI_STRENGTH

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=TYPE_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=TYPE_WIFI_STRENGTH,
        translation_key="wifi_rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Initialize a Blink sensor."""
    data = hass.data[DOMAIN][config.entry_id]
    entities = [
        BlinkSensor(data, camera, description)
        for camera in data.cameras
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities, update_before_add=True)


class BlinkSensor(SensorEntity):
    """A Blink camera sensor."""

    _attr_has_entity_name = True

    def __init__(self, data, camera, description: SensorEntityDescription) -> None:
        """Initialize sensors from Blink camera."""
        self.entity_description = description
        self.data = data
        self._camera = data.cameras[camera]
        self._attr_unique_id = f"{self._camera.serial}-{description.key}"
        self._sensor_key = (
            "temperature_calibrated"
            if description.key == "temperature"
            else description.key
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._camera.serial)},
            name=f"{DOMAIN} {camera}",
            manufacturer=DEFAULT_BRAND,
            model=self._camera.camera_type,
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Retrieve sensor data from the camera."""
        try:
            native_value = self._camera.attributes[self._sensor_key]
            _LOGGER.debug(
                "'%s' %s = %s",
                self._camera.attributes["name"],
                self._sensor_key,
                self._attr_native_value,
            )
        except KeyError:
            native_value = None
            _LOGGER.error(
                "%s not a valid camera attribute. Did the API change?", self._sensor_key
            )
        return native_value
