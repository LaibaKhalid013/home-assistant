"""Support for Nederlandse Spoorwegen public transport."""
from datetime import datetime, timedelta
import logging

import ns_api
from ns_api import RequestParametersError
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_API_KEY, CONF_NAME
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by NS"

CONF_ROUTES = "routes"
CONF_FROM = "from"
CONF_TO = "to"
CONF_VIA = "via"
CONF_TIME = "time"
CONF_OFFSET = "offset"

ICON = "mdi:train"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=120)

ROUTE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_FROM): cv.string,
        vol.Required(CONF_TO): cv.string,
        vol.Optional(CONF_VIA): cv.string,
        vol.Optional(CONF_TIME): cv.time,
        vol.Optional(CONF_OFFSET): cv.positive_int,
    }
)

ROUTES_SCHEMA = vol.All(cv.ensure_list, [ROUTE_SCHEMA])

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_API_KEY): cv.string, vol.Optional(CONF_ROUTES): ROUTES_SCHEMA}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the departure sensor."""

    nsapi = ns_api.NSAPI(config[CONF_API_KEY])

    try:
        stations = nsapi.get_stations()
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ) as error:
        _LOGGER.error("Could not connect to the internet: %s", error)
        raise PlatformNotReady() from error
    except RequestParametersError as error:
        _LOGGER.error("Could not fetch stations, please check configuration: %s", error)
        return

    sensors = []
    for departure in config.get(CONF_ROUTES):
        if not valid_stations(
            stations,
            [departure.get(CONF_FROM), departure.get(CONF_VIA), departure.get(CONF_TO)],
        ):
            continue
        sensors.append(
            NSDepartureSensor(
                nsapi,
                departure.get(CONF_NAME),
                departure.get(CONF_FROM),
                departure.get(CONF_TO),
                departure.get(CONF_VIA),
                departure.get(CONF_TIME),
                departure.get(CONF_OFFSET),
            )
        )
    if sensors:
        add_entities(sensors, True)


def valid_stations(stations, given_stations):
    """Verify the existence of the given station codes."""
    for station in given_stations:
        if station is None:
            continue
        if not any(s.code == station.upper() for s in stations):
            _LOGGER.warning("Station '%s' is not a valid station", station)
            return False
    return True


class NSDepartureSensor(Entity):
    """Implementation of a NS Departure Sensor."""

    def __init__(self, nsapi, name, departure, heading, via, time, offset):
        """Initialize the sensor."""
        self._nsapi = nsapi
        self._name = name
        self._departure = departure
        self._via = via
        self._heading = heading
        self._time = time
        self._offset = offset
        self._state = None
        self._trips = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon for the frontend."""
        return ICON

    @property
    def state(self):
        """Return the next departure time."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if not self._trips:
            return

        if self._trips[0].trip_parts:
            route = [self._trips[0].departure]
            for k in self._trips[0].trip_parts:
                route.append(k.destination)

        # Static attributes
        attributes = {
            "going": self._trips[0].going,
            "departure_time_planned": None,
            "departure_time_actual": None,
            "departure_delay": False,
            "departure_platform_planned": self._trips[0].departure_platform_planned,
            "departure_platform_actual": self._trips[0].departure_platform_actual,
            "arrival_time_planned": None,
            "arrival_time_actual": None,
            "arrival_delay": False,
            "arrival_platform_planned": self._trips[0].arrival_platform_planned,
            "arrival_platform_actual": self._trips[0].arrival_platform_actual,
            "next": None,
            "status": self._trips[0].status.lower(),
            "transfers": self._trips[0].nr_transfers,
            "route": route,
            "remarks": None,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

        # Planned departure attributes
        if self._trips[0].departure_time_planned is not None:
            attributes["departure_time_planned"] = self._trips[
                0
            ].departure_time_planned.strftime("%H:%M")

        # Actual departure attributes
        if self._trips[0].departure_time_actual is not None:
            attributes["departure_time_actual"] = self._trips[
                0
            ].departure_time_actual.strftime("%H:%M")

        # Delay departure attributes
        if (
            attributes["departure_time_planned"]
            and attributes["departure_time_actual"]
            and attributes["departure_time_planned"]
            != attributes["departure_time_actual"]
        ):
            attributes["departure_delay"] = True

        # Planned arrival attributes
        if self._trips[0].arrival_time_planned is not None:
            attributes["arrival_time_planned"] = self._trips[
                0
            ].arrival_time_planned.strftime("%H:%M")

        # Actual arrival attributes
        if self._trips[0].arrival_time_actual is not None:
            attributes["arrival_time_actual"] = self._trips[
                0
            ].arrival_time_actual.strftime("%H:%M")

        # Delay arrival attributes
        if (
            attributes["arrival_time_planned"]
            and attributes["arrival_time_actual"]
            and attributes["arrival_time_planned"] != attributes["arrival_time_actual"]
        ):
            attributes["arrival_delay"] = True

        # Next attributes
        if len(self._trips) > 1:
            if self._trips[1].departure_time_actual is not None:
                attributes["next"] = self._trips[1].departure_time_actual.strftime(
                    "%H:%M"
                )
            elif self._trips[1].departure_time_planned is not None:
                attributes["next"] = self._trips[1].departure_time_planned.strftime(
                    "%H:%M"
                )

        return attributes

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the trip information."""

        # If looking for a specific trip time, update around that trip time only.
        if self._time and (
            (datetime.now() + timedelta(minutes=30)).time() < self._time
            or (datetime.now() - timedelta(minutes=30)).time() > self._time
        ):
            self._state = None
            self._trips = None
            return

        # Set the search parameter to search from a specific trip time or to just search for next trip.
        if self._time:
            trip_time = (
                datetime.today()
                .replace(hour=self._time.hour, minute=self._time.minute)
                .strftime("%d-%m-%Y %H:%M")
            )
        else:
            if self._offset:
                offset_time = datetime.now() + timedelta(minutes=self._offset)
                trip_time = offset_time.strftime("%d-%m-%Y %H:%M")
            else:
                trip_time = datetime.now().strftime("%d-%m-%Y %H:%M")
                
        try:
            self._trips = self._nsapi.get_trips(
                trip_time, self._departure, self._via, self._heading, True, 0, 2
            )
            if self._trips:
                if self._trips[0].departure_time_actual is None:
                    planned_time = self._trips[0].departure_time_planned
                    self._state = planned_time.strftime("%H:%M")
                else:
                    actual_time = self._trips[0].departure_time_actual
                    self._state = actual_time.strftime("%H:%M")
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ) as error:
            _LOGGER.error("Couldn't fetch trip info: %s", error)
