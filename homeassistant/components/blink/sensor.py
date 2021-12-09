"""Support for Blink system camera sensors."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, TEMP_FAHRENHEIT

from .const import DOMAIN, TYPE_TEMPERATURE, TYPE_WIFI_STRENGTH

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=TYPE_TEMPERATURE,
        name="Temperature",
        native_unit_of_measurement=TEMP_FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        key=TYPE_WIFI_STRENGTH,
        name="Wifi Signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    ),
)


async def async_setup_entry(hass, config, async_add_entities):
    """Initialize a Blink sensor."""
    data = hass.data[DOMAIN][config.entry_id]
    entities = [
        BlinkSensor(data, camera, description)
        for camera in data.cameras
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class BlinkSensor(SensorEntity):
    """A Blink camera sensor."""

    def __init__(self, data, camera, description: SensorEntityDescription):
        """Initialize sensors from Blink camera."""
        self.entity_description = description
        self._attr_name = f"{DOMAIN} {camera} {description.name}"
        self.data = data
        self._camera = data.cameras[camera]
        self._attr_unique_id = f"{self._camera.serial}-{description.key}"
        self._sensor_key = (
            "temperature_calibrated"
            if description.key == "temperature"
            else description.key
        )

    def update(self):
        """Retrieve sensor data from the camera."""
        self.data.refresh()
        try:
            self._attr_native_value = self._camera.attributes[self._sensor_key]
        except KeyError:
            self._attr_native_value = None
            _LOGGER.error(
                "%s not a valid camera attribute. Did the API change?", self._sensor_key
            )
