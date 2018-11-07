"""
A sensor platform that give you information about the next space launch.

For more details about this platform, please refer to the documentation at
https://www.home-assistant.io/components/sensor.launch/
"""
from datetime import timedelta
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

REQUIREMENTS = ['pylaunches==0.1.1']

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Data provided by Launch Library."

DEFAULT_NAME = 'Launch'

TIME_BETWEEN_UPDATES = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    })


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Create the launch sensor."""
    from pylaunches.api import Launches

    name = config[CONF_NAME]

    session = async_get_clientsession(hass)
    launches = LaunchData(Launches(hass.loop, session))
    sensor = [LaunchSensor(launches, name)]
    async_add_entities(sensor, True)


class LaunchSensor(Entity):
    """Representation of a launch Sensor."""

    def __init__(self, launches, name):
        """Initialize the sensor."""
        self.launches = launches
        self._attributes = {}
        self._name = name
        self._state = None

    async def async_update(self):
        """Get the latest data."""
        await self.launches.async_update()
        if self.launches.api.launches is None:
            _LOGGER.error("No data recieved.")
            return
        try:
            data = self.launches.api.launches[0]
            self._state = data['name']
            self._attributes['launch_time'] = data['start']
            self._attributes['agency'] = data['agency']
            self._attributes['agency_country_code'] = (data
                                                       ['agency_country_code'])
            self._attributes['stream'] = data['stream']
            self._attributes[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION
        except (KeyError, IndexError) as error:
            _LOGGER.debug("Error getting data, %s", error)

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
        """Return the icon of the sensor."""
        return 'mdi:rocket'

    @property
    def device_state_attributes(self):
        """Return attributes for the sensor."""
        return self._attributes


class LaunchData():
    """Get the latest data and update the states."""

    def __init__(self, api):
        """Initialize the data object."""
        self.api = api

    @Throttle(TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the latest launch data."""
        await self.api.get_launches()
