"""
Sensor support for Skybell Doorbells.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.skybell/
"""
from datetime import timedelta
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.skybell import (
    DEFAULT_ENTITY_NAMESPACE, DOMAIN as SKYBELL_DOMAIN, SkybellDevice)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_ENTITY_NAMESPACE, CONF_MONITORED_CONDITIONS, STATE_UNKNOWN)

DEPENDENCIES = ['skybell']

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

# Sensor types: Name, icon, unit
SENSOR_TYPES = {
    'chime_level': ['Chime Level', 'bell-ring', None],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ENTITY_NAMESPACE, default=DEFAULT_ENTITY_NAMESPACE):
        cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the platform for a Skybell device."""
    skybell = hass.data.get(SKYBELL_DOMAIN)

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        for device in skybell.get_devices():
            sensors.append(SkybellSensor(device, sensor_type))

    add_devices(sensors, True)
    return True


class SkybellSensor(SkybellDevice):
    """A sensor implementation for Skybell devices."""

    def __init__(self, device, sensor_type):
        """Initialize a sensor for a Skybell device."""
        SkybellDevice.__init__(self, device)
        self._sensor_type = sensor_type
        self._icon = 'mdi:{}'.format(SENSOR_TYPES.get(self._sensor_type)[1])
        self._name = "{0} {1}".format(self._device.name,
                                      SENSOR_TYPES.get(self._sensor_type)[0])
        self._device_class = SENSOR_TYPES.get(self._sensor_type)[1]
        self._state = STATE_UNKNOWN

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return SENSOR_TYPES.get(self._sensor_type)[2]

    def update(self):
        """Get the latest data and updates the state."""
        SkybellDevice.update(self)

        if self._sensor_type == 'chime_level':
            self._state = self._device.outdoor_chime_level
