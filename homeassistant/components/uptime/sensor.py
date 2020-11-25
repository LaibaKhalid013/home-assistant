"""Platform to retrieve uptime for Home Assistant."""
import logging

import voluptuous as vol

from homeassistant.components.sensor import DEVICE_CLASS_TIMESTAMP, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Uptime"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the uptime sensor platform."""
    name = config.get(CONF_NAME)

    async_add_entities([UptimeSensor(name)], True)


class UptimeSensor(Entity):
    """Representation of an uptime sensor."""

    def __init__(self, name):
        """Initialize the uptime sensor."""
        self._name = name
        self.initial = dt_util.now().isoformat()
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_class(self):
        """Return device class."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Update the state of the sensor."""
        self._state = self.initial
