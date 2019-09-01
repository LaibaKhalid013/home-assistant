# -*- coding: utf-8 -*-
"""
Service for obtaining information about closer bus from Transport Yandex Service
"""

import logging
from datetime import timedelta

import voluptuous as vol
from moscow_yandex_transport import YandexMapsRequester

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

STOP_NAME = "Stop name"
USER_AGENT = "Home Assistant"
ATTRIBUTION = "Data provided by maps.yandex.ru"

CONF_STOP_ID = "stop_id"
CONF_ROUTE = "routes"

DEFAULT_NAME = "Yandex Transport"
ICON = "mdi:bus"

SCAN_INTERVAL = timedelta(minutes=1)
TIME_STR_FORMAT = "%H:%M"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STOP_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_ROUTE, default=[]): vol.All(cv.ensure_list, [cv.string]),

    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Yandex transport sensor."""
    stop_id = config[CONF_STOP_ID]
    name = config[CONF_NAME]
    routes = config[CONF_ROUTE]

    data = YandexMapsRequester(user_agent=USER_AGENT)
    add_entities([DiscoverMoscowYandexTransport(data, stop_id, routes, name)], True)


class DiscoverMoscowYandexTransport(Entity):
    def __init__(self, requester, stop_id, routes, name):
        """Initialize sensor."""
        self.requester = requester
        self._stop_id = stop_id
        self._routes = []
        self._routes = routes
        self._state = None
        self._name = name
        self._attrs = None

    def update(self):
        """Get the latest data from maps.yandex.ru and update the states."""
        attrs = {}
        closer_time = None
        try:
            yandex_reply = self.requester.get_stop_info(self._stop_id)
            data = yandex_reply["data"]
            stop_metadata = data["properties"]["StopMetaData"]
        except KeyError as e:
            _LOGGER.warning(
                "Exception KeyError was captured, missing key is " + str(e) + ". Yandex returned: " + str(yandex_reply))
            self.requester.set_new_session()
            data = self.requester.get_stop_info(self._stop_id)["data"]
            stop_metadata = data["properties"]["StopMetaData"]
        stop_name = data["properties"]["name"]
        transport_list = stop_metadata["Transport"]
        for transport in transport_list:
            route = transport["name"]
            if route not in self._routes:
                # skip unnecessary route info
                continue
            if "Events" in transport["BriefSchedule"]:
                for event in transport["BriefSchedule"]["Events"]:
                    if "Estimated" in event:
                        posix_time_next = int(event["Estimated"]["value"])
                        if closer_time is None or closer_time > posix_time_next:
                            closer_time = posix_time_next
                        if route not in attrs:
                            attrs[route] = []
                        attrs[route].append(event["Estimated"]["text"])
        attrs[STOP_NAME] = stop_name
        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
        if closer_time is None:
            self._state = None
        else:
            self._state = closer_time
        self._attrs = attrs

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "timestamp"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON
