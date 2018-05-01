"""
Sensor for PostNL packages.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.postnl/
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD,
                                 ATTR_ATTRIBUTION)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['postnl_api==1.0.1']

_LOGGER = logging.getLogger(__name__)
DEFAULT_NAME = 'postnl'
ICON = 'mdi:package-variant-closed'
ATTRIBUTION = 'Information provided by PostNL'
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

# pylint: disable=unused-argument


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the PostNL platform."""

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    name = config.get(CONF_NAME)

    from postnl_api import PostNL_API, UnauthorizedException

    try:
        api = PostNL_API(username, password)

    except UnauthorizedException:
        _LOGGER.exception("Can't connect to the PostNL webservice")
        return

    add_devices([PostNLSensor(api, name)], True)


class PostNLSensor(Entity):
    """PostNL Sensor."""

    def __init__(self, api, name):
        """Initialize the sensor."""
        self._name = name
        self._attributes = None
        self._state = None
        self._api = api

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
        """Return the unit of measurement of this entity, if any."""
        return 'package(s)'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update device state."""

        shipments = self._api.get_relevant_shipments()
        status_counts = {}

        for shipment in shipments:
            status = shipment['status']['formatted']['short']
            status = self._api.parse_datetime(status, '%d-%m-%Y', '%H:%M')

            name = shipment['settings']['title']
            status_counts[name] = status

        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            **status_counts
        }

        self._state = len(status_counts)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON
