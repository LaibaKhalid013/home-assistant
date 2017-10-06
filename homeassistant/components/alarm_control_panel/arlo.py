"""
This component provides HA alarm_control_panel support for Arlo System.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.arlo/
"""
import asyncio
import logging
import voluptuous as vol

from homeassistant.components.arlo import (DATA_ARLO, CONF_ATTRIBUTION)
from homeassistant.components.alarm_control_panel import (AlarmControlPanel,
                                                          PLATFORM_SCHEMA)
from homeassistant.const import (ATTR_ATTRIBUTION, STATE_ALARM_ARMED_AWAY,
                                 STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED)
import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ['arlo']

_LOGGER = logging.getLogger(__name__)

CONF_HOME_MODE_NAME = 'home_mode_name'
ICON = 'mdi:security'
ARMED = "armed"
DISARMED = "disarmed"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOME_MODE_NAME, default=ARMED): cv.string,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up a sensor for an Arlo device."""
    data = hass.data[DATA_ARLO]

    if not data.base_stations:
        return

    home_mode_name = config.get(CONF_HOME_MODE_NAME)
    base_stations = []
    for base_station in data.base_stations:
        base_stations.append(ArloBaseStation(base_station, home_mode_name))
    async_add_devices(base_stations)


class ArloBaseStation(AlarmControlPanel):
    """An alarm_control_panel implementation for Arlo."""

    def __init__(self, data, home_mode_name):
        """Initialize the alarm control panel."""
        self._base_station = data
        self._home_mode_name = home_mode_name
        self._state = self._base_station.mode

    @property
    def icon(self):
        """Return icon."""
        return ICON

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @asyncio.coroutine
    def async_update(self):
        """Update the state of the device."""
        # PyArlo sometimes returns None for mode. So retry 3 times before
        # returning None.
        num_retries = 3
        i = 0
        while i < num_retries:
            mode = self._base_station.mode
            if mode:
                self._state = self._get_state_from_mode(mode)
                return self._state
            i += 1
        self._state = None
        return self._state

    @asyncio.coroutine
    def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        self._base_station.mode = DISARMED

    @asyncio.coroutine
    def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._base_station.mode = ARMED

    @asyncio.coroutine
    def async_alarm_arm_home(self, code=None):
        """Send arm home command. Uses custom mode."""
        self._base_station.mode = self._home_mode_name

    @property
    def name(self):
        """Return the name of the base station."""
        return self._base_station.name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
            'device_id': self._base_station.device_id
        }

    def _get_state_from_mode(self, mode):
        if mode == ARMED:
            return STATE_ALARM_ARMED_AWAY
        elif mode == DISARMED:
            return STATE_ALARM_DISARMED
        elif mode == self._home_mode_name:
            return STATE_ALARM_ARMED_HOME
        return None
