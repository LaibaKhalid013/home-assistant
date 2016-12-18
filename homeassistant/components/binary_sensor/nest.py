"""
Support for Nest Thermostat Binary Sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.nest/
"""
from itertools import chain
import logging

from homeassistant.components.binary_sensor import (BinarySensorDevice)
from homeassistant.components.sensor.nest import NestSensor
from homeassistant.const import (CONF_MONITORED_CONDITIONS)
from homeassistant.components.nest import (DATA_NEST, is_thermostat, is_camera)

DEPENDENCIES = ['nest']

BINARY_TYPES = ['online']

CLIMATE_BINARY_TYPES = ['fan',
                        'is_using_emergency_heat',
                        'is_locked',
                        'has_leaf']

CAMERA_BINARY_TYPES = [
    'motion_detected',
    'sound_detected',
    'person_detected']

_BINARY_TYPES_DEPRECATED = [
    'hvac_ac_state',
    'hvac_aux_heater_state',
    'hvac_heater_state',
    'hvac_heat_x2_state',
    'hvac_heat_x3_state',
    'hvac_alt_heat_state',
    'hvac_alt_heat_x2_state',
    'hvac_emer_heat_state']

_VALID_BINARY_SENSOR_TYPES = BINARY_TYPES + CLIMATE_BINARY_TYPES \
    + CAMERA_BINARY_TYPES

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup Nest binary sensors."""
    if discovery_info is None:
        return

    nest = hass.data[DATA_NEST]

    """Add Nest Protect sensors if no binary sensor config is specified"""
    if discovery_info == {}:
        conditions = BINARY_TYPES
    else:
        conditions = discovery_info.get(CONF_MONITORED_CONDITIONS, {})
        """Add all binary sensors if no monitored conditions are specified"""
        if all(c is None for c in conditions):
            conditions = _VALID_BINARY_SENSOR_TYPES

    for variable in conditions:
        if variable in _BINARY_TYPES_DEPRECATED:
            wstr = (variable + " is no a longer supported "
                    "monitored_conditions. See "
                    "https://home-assistant.io/components/binary_sensor.nest/ "
                    "for valid options.")
            _LOGGER.error(wstr)

    sensors = []
    device_chain = chain(nest.devices(),
                         nest.protect_devices(),
                         nest.camera_devices())
    for structure, device in device_chain:
        sensors += [NestBinarySensor(structure, device, variable)
                    for variable in conditions
                    if variable in BINARY_TYPES]
        sensors += [NestBinarySensor(structure, device, variable)
                    for variable in conditions
                    if variable in CLIMATE_BINARY_TYPES
                    and is_thermostat(device)]

        if is_camera(device):
            sensors += [NestBinarySensor(structure, device, variable)
                        for variable in conditions
                        if variable in CAMERA_BINARY_TYPES]
            for activity_zone in device.activity_zones:
                sensors += [NestActivityZoneSensor(structure,
                                                   device,
                                                   activity_zone)]

    add_devices(sensors, True)


class NestBinarySensor(NestSensor, BinarySensorDevice):
    """Represents a Nest binary sensor."""

    @property
    def is_on(self):
        """True if the binary sensor is on."""
        return self._state

    def update(self):
        """Retrieve latest state."""
        self._state = bool(getattr(self.device, self.variable))


class NestActivityZoneSensor(NestBinarySensor):
    """Represents a Nest binary sensor for activity in a zone."""

    def __init__(self, structure, device, zone):
        """Initialize the sensor."""
        super(NestActivityZoneSensor, self).__init__(structure, device, None)
        self.zone = zone

    @property
    def name(self):
        """Return the name of the nest, if any."""
        return "{} {} activity".format(self._name, self.zone.name)

    def update(self):
        """Retrieve latest state."""
        self._state = self.device.has_ongoing_motion_in_zone(self.zone.zone_id)
