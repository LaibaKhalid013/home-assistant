"""
homeassistant.components.binary.nest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Nest Thermostat Binary Sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.nest/
"""
import logging
import socket
import homeassistant.components.nest as nest

from homeassistant.components.sensor.nest import NestSensor
from homeassistant.components.binary_sensor import BinarySensorDevice


BINARY_TYPES = ['fan',
                'hvac_ac_state',
                'hvac_aux_heater_state',
                'hvac_heat_x2_state',
                'hvac_heat_x3_state',
                'hvac_alt_heat_state',
                'hvac_alt_heat_x2_state',
                'hvac_emer_heat_state',
                'online']


def setup_platform(hass, config, add_devices, discovery_info=None):
    "Setup nest binary sensors from config file"

    logger = logging.getLogger(__name__)
    try:
        for structure in nest.NEST.structures:
            for device in structure.devices:
                for variable in config['monitored_conditions']:
                    if variable in BINARY_TYPES:
                        add_devices([NestBinarySensor(structure,
                                                      device,
                                                      variable)])
                    else:
                        logger.error('Nest sensor type: "%s" does not exist',
                                     variable)
    except socket.error:
        logger.error(
            "Connection error logging into the nest web service."
        )


class NestBinarySensor(NestSensor, BinarySensorDevice):
    """ Represents a Nst Binary sensor. """

    @property
    def is_on(self):
        "Returns is the binary sensor is on or off"

        return bool(getattr(self.device, self.variable))
