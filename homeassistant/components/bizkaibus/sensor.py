
"""Support for Bizkaibus, Biscay (Basque Country, Spain) Bus service."""

import logging
import requests
import json

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from bizkaibus import BizkaibusData

import xml.etree.ElementTree as ET

_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'http://apli.bizkaia.net/'
_RESOURCE += 'APPS/DANOK/TQWS/TQ.ASMX/GetPasoParadaMobile_JSON'

ATTR_ROUTE = 'Route'
ATTR_ROUTE_NAME = 'Route name'
ATTR_DUE_IN = 'Due in'

CONF_STOP_ID = 'stopid'
CONF_ROUTE = 'route'

DEFAULT_NAME = 'Next bus'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_STOP_ID): cv.string,
    vol.Optional(CONF_ROUTE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Bizkaibus public transport sensor."""
    name = config.get(CONF_NAME)
    stop = config.get(CONF_STOP_ID)
    route = config.get(CONF_ROUTE)

    data = BizkaibusData(stop, route)
    add_entities([BizkaibusSensor(data, stop, route, name)], True)


class BizkaibusSensor(Entity):
    """The class for handling the data."""

    def __init__(self, data, stop, route, name):
        """Initialize the sensor."""
        self.data = data
        self.stop = stop
        self.route = route
        self._name = name
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return 'min'

    def update(self):
        """Get the latest data from the webservice."""
        self.data.update()
        try:
            self._state = self.data.info[0][ATTR_DUE_IN]
        except TypeError:
            pass


class Bizkaibus:
    """The class for handling the data retrieval."""

    def __init__(self, stop, route):
        """Initialize the data object."""
        self.stop = stop
        self.route = route
        self.info = [{ATTR_ROUTE_NAME: 'n/a',
                      ATTR_ROUTE: self.route,
                      ATTR_DUE_IN: 'n/a'}]

    def update(self):
        """Retrieve the information from API."""
        bridge = BizkaibusData(self.stop, self.route)
        bridge.getNextBus()
        status = bridge.info
