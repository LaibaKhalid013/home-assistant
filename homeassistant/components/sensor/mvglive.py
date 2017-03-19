"""
Support for real-time departure information for public transport in Munich.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.mvglive/
"""

import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
# A typo in the file name of the PyPI version prevents installation from PyPI
REQUIREMENTS = ["https://github.com/pc-coholic/PyMVGLive/archive/"
                "1.1.2.zip#"
                "PyMVGLive==1.1.2"]
ICON = 'mdi:bus'

# Return cached results if last scan was less then this time ago.
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=15)

CONF_STATION = 'station'
CONF_DEST = 'destination'
CONF_LINE = 'line'
CONF_OFFSET = 'offset'
CONF_UBAHN = 'ubahn'
CONF_TRAM = 'tram'
CONF_BUS = 'bus'
CONF_SBAHN = 'sbahn'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_STATION): cv.string,
    vol.Optional(CONF_DEST, default=None): cv.string,
    vol.Optional(CONF_LINE, default=None): cv.string,
    vol.Optional(CONF_OFFSET, default=0): cv.positive_int,
    vol.Optional(CONF_UBAHN, default=True): cv.boolean,
    vol.Optional(CONF_TRAM, default=True): cv.boolean,
    vol.Optional(CONF_BUS, default=True): cv.boolean,
    vol.Optional(CONF_SBAHN, default=True): cv.boolean,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the MVG Live Sensor."""
    station = config.get(CONF_STATION)
    destination = config.get(CONF_DEST)
    line = config.get(CONF_LINE)
    offset = config.get(CONF_OFFSET)
    ubahn = config.get(CONF_UBAHN)
    tram = config.get(CONF_TRAM)
    bus = config.get(CONF_BUS)
    sbahn = config.get(CONF_SBAHN)

    add_devices([MVGLiveSensor(station, destination, line,
                               offset, ubahn, tram, bus, sbahn)])


# pylint: disable=too-few-public-methods
class MVGLiveSensor(Entity):
    """Implementation of an MVG Live sensor."""

    def __init__(self, station, destination, line,
                 offset, ubahn, tram, bus, sbahn):
        """Initialize the sensor."""
        self._station = station
        self._destination = destination
        self._line = line
        self.data = MVGLiveData(station, destination, line,
                                offset, ubahn, tram, bus, sbahn)
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        # e.g.
        # 'Hauptbahnhof (S1)'
        # 'Hauptbahnhof-Marienplatz'
        # 'Hauptbahnhof-Marienplatz (S1)'
        namestr = self._station
        if self._destination:
            namestr = namestr + '-' + self._destination
        if self._line:
            namestr = namestr + ' (' + self._line + ')'
        return namestr

    @property
    def icon(self):
        """Return the icon for the frontend."""
        return ICON

    @property
    def state(self):
        """Return the departure time of the next train."""
        return self._state

    @property
    def state_attributes(self):
        """Return the state attributes."""
        if self.data.departures:
            return self.data.departures[0]

    def update(self):
        """Get the latest data and update the state."""
        self.data.update()
        if not self.data.departures:
            self._state = ('-')
        else:
            self._state = self.data.departures[0].get('time', '-')


class MVGLiveData(object):
    """Pull data from the mvg-live.de web page."""

    def __init__(self, station, destination, line,
                 offset, ubahn, tram, bus, sbahn):
        """Initialize the sensor."""
        import MVGLive
        self._station = station
        self._destination = destination
        self._line = line
        self._offset = offset
        self._ubahn = ubahn
        self._tram = tram
        self._bus = bus
        self._sbahn = sbahn
        self.mvg = MVGLive.MVGLive()
        self.departures = [{}]

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the connection data."""
        try:
            self.departures = self.mvg.getlivedata(station=self._station,
                                                   ubahn=self._ubahn,
                                                   tram=self._tram,
                                                   bus=self._bus,
                                                   sbahn=self._sbahn)
        except ValueError:
            self.departures = [{}]
            _LOGGER.warning("Returned data not understood.")
            return
        self.departures = [con for con in self.departures
                           if con['time'] >= self._offset and
                           con['destination'].startswith(self._destination)]
        for con in self.departures:
            # Details info is not useful.
            # Having a more consistent interface simplifies
            # usage of Template sensors later on
            con.pop('productsymbol')
            con.pop('productsymbolurl')
            con.pop('linesymbol')
            con.pop('linesymbolurl')
            if 'time' in con and con['time'].is_integer():
                con['time'] = int(con['time'])
