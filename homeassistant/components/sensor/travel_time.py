"""
Support for RFXtrx sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.travel_time/
"""
from datetime import datetime
import logging
import voluptuous as vol

from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_API_KEY, TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['googlemaps']

CONF_ORIGIN = 'origin'
CONF_DESTINATION = 'destination'
CONF_TRAVEL_MODE = 'travel_mode'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required('platform'): 'travel_time',
    vol.Required(CONF_API_KEY): vol.Coerce(str),
    vol.Required(CONF_ORIGIN): vol.Coerce(str),
    vol.Required(CONF_DESTINATION): vol.Coerce(str),
    vol.Optional(CONF_TRAVEL_MODE, default='driving'):
        vol.In(["driving", "walking", "bicycling", "transit"])
})


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the RFXtrx platform."""
    # pylint: disable=too-many-locals

    is_metric = (hass.config.temperature_unit == TEMP_CELSIUS)
    api_key = config.get(CONF_API_KEY)
    origin = config.get(CONF_ORIGIN)
    destination = config.get(CONF_DESTINATION)
    travel_mode = config.get(CONF_TRAVEL_MODE)

    sensor = GoogleMapsSensor(api_key, origin, destination,
                              travel_mode, is_metric)
    add_devices_callback([sensor])


class GoogleMapsSensor(Entity):
    """Representation of a tavel time sensor."""

    # pylint: disable=too-many-arguments
    def __init__(self, api_key, origin, destination, travel_mode, is_metric):
        """Initialize the sensor."""
        if is_metric:
            self._unit = 'metric'
        else:
            self._unit = 'imperial'
        self._origin = origin
        self._destination = destination
        self._travel_mode = travel_mode
        self._name = "Travel time"
        self._matrix = None

        import googlemaps
        self._client = googlemaps.Client(api_key, timeout=10)
        self.update()

    def __str__(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._matrix['rows'][0]['elements'][0]['duration']['value']/60.0

    @property
    def name(self):
        """Get the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        res = self._matrix.copy()
        del res['rows']
        _data = self._matrix['rows'][0]['elements'][0]
        if 'duration_in_traffic' in _data:
            res['duration_in_traffic'] = _data['duration_in_traffic']['text']
        if 'duration' in _data:
            res['duration'] = _data['duration']['text']
        if 'distance' in _data:
            res['distance'] = _data['distance']['text']
        return res

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "min"

    def update(self):
        """Get the latest data from Google."""
        now = datetime.now()
        self._matrix = self._client.distance_matrix(self._origin,
                                                    self._destination,
                                                    mode=self._travel_mode,
                                                    units=self._unit,
                                                    departure_time=now,
                                                    traffic_model="optimistic")
