"""
Support for Meteo France raining forecast.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.meteofrance/
"""

import logging
import datetime
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, STATE_UNKNOWN, ATTR_ATTRIBUTION, TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['meteofrance==0.2.0']
_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Data provided by Meteo-France"
CONF_POSTAL_CODE = 'postal_code'

STATE_ATTR_FORECAST = 'Forecast'

SCAN_INTERVAL = datetime.timedelta(minutes=1)

SENSOR_TYPES = {
    'rain_chance': ['Rain chance', '%'],
    'freeze_chance': ['Freeze chance', '%'],
    'thunder_chance': ['Thunder chance', '%'],
    'snow_chance': ['Snow chance', '%'],
    'weather': ['Weather', None],
    'wind_speed': ['Wind Speed', 'km/h'],
    'next_rain': ['Next rain', 'min'],
    'temperature': ['Temperature', TEMP_CELSIUS],
    'uv': ['UV', None],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_POSTAL_CODE): cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Meteo-France sensor."""
    postal_code = config.get(CONF_POSTAL_CODE)

    from meteofrance.client import meteofranceClient, meteofranceError

    try:
        meteofrance_client = meteofranceClient(postal_code)
    except meteofranceError as exp:
        _LOGGER.error(exp)
        return

    client = MeteoFranceUpdater(meteofrance_client)

    add_devices([MeteoFranceSensor('Météo-France', variable, client)
                 for variable in config[CONF_MONITORED_CONDITIONS]])


class MeteoFranceSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, condition, client):
        """Initialize the sensor."""
        self._name = name
        self._condition = condition
        self._client = client
        self._data = client.get_data()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._data["name"]+' '+SENSOR_TYPES[self._condition][0]

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._data[self._condition] is not False:
            return self._data[self._condition]
        return STATE_UNKNOWN

    @property
    def state_attributes(self):
        """Return the state attributes of the sun."""
        if self._condition == 'next_rain':
            return {
                **{
                    STATE_ATTR_FORECAST: self._data["rain_forecast"],
                },
                ** self._data["next_rain_intervals"],
                **{
                    ATTR_ATTRIBUTION: CONF_ATTRIBUTION
                }
            }
        return {ATTR_ATTRIBUTION: CONF_ATTRIBUTION}

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SENSOR_TYPES[self._condition][1]

    def update(self):
        """Fetch new state data for the sensor."""
        self._client.update()


class MeteoFranceUpdater:
    """Update data from Meteo-France."""

    def __init__(self, client):
        """Initialize the data object."""
        self._client = client

    def get_data(self):
        """Get the latest data from Meteo-France."""
        return self._client.get_data()

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest data from Meteo-France."""
        _LOGGER.error("updating meteofrance")
        from meteofrance.client import meteofranceError
        try:
            self._client.update()
        except meteofranceError as exp:
            _LOGGER.error(exp)
            return
