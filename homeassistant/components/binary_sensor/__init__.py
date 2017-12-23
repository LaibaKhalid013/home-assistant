"""
Component to interface with binary sensors.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/binary_sensor/
"""
import asyncio
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from homeassistant.const import (STATE_ON, STATE_OFF)
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa

DOMAIN = 'binary_sensor'
SCAN_INTERVAL = timedelta(seconds=30)

ENTITY_ID_FORMAT = DOMAIN + '.{}'
DEVICE_CLASSES = [
    'battery',       # On means low, Off means normal
    'cold',          # On means cold (or too cold)
    'connectivity',  # On means connection present, Off = no connection
    'door',          # On means open, Off means closed
    'garage_door',   # On means open, Off means closed
    'gas',           # CO, CO2, etc.
    'heat',          # On means hot (or too hot)
    'light',         # Lightness threshold
    'moisture',      # Specifically a wetness sensor
    'motion',        # Motion sensor
    'moving',        # On means moving, Off means stopped
    'occupancy',     # On means occupied, Off means not occupied
    'opening',       # Generic contact sensor, On means open, Off means closed
    'plug',          # On means plugged in, Off means unplugged
    'power',         # Power, over-current, etc
    'presence',      # On means home, Off means away
    'problem',       # On means there is a problem, Off means the status is OK
    'safety',        # Generic on=unsafe, off=safe
    'smoke',         # Smoke detector
    'sound',         # On means sound detected, Off means no sound
    'vibration',     # On means vibration detected, Off means no vibration
    'window',        # On means open, Off means closed
]

DEVICE_CLASSES_SCHEMA = vol.All(vol.Lower, vol.In(DEVICE_CLASSES))


@asyncio.coroutine
def async_setup(hass, config):
    """Track states and offer events for binary sensors."""
    component = EntityComponent(
        logging.getLogger(__name__), DOMAIN, hass, SCAN_INTERVAL)

    yield from component.async_setup(config)
    return True


# pylint: disable=no-self-use
class BinarySensorDevice(Entity):
    """Represent a binary sensor."""

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return None

    @property
    def state(self):
        """Return the state of the binary sensor."""
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return None
