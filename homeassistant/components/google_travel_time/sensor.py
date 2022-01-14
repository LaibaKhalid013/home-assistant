"""Support for Google travel time sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from googlemaps import Client
from googlemaps.distance_matrix import distance_matrix

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_MODE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STARTED,
    TIME_MINUTES,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.location import find_coordinates
import homeassistant.util.dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_ARRIVAL_TIME,
    CONF_DEPARTURE_TIME,
    CONF_DESTINATION,
    CONF_OPTIONS,
    CONF_ORIGIN,
    CONF_TRAVEL_MODE,
    CONF_UNITS,
    DEFAULT_NAME,
    DOMAIN,
    TRACKABLE_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)


def convert_time_to_utc(timestr):
    """Take a string like 08:00:00 and convert it to a unix timestamp."""
    combined = datetime.combine(
        dt_util.start_of_local_day(), dt_util.parse_time(timestr)
    )
    if combined < datetime.now():
        combined = combined + timedelta(days=1)
    return dt_util.as_timestamp(combined)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Google travel time sensor entry."""
    if not config_entry.options:
        new_data = config_entry.data.copy()
        options = new_data.pop(CONF_OPTIONS, {})

        if CONF_UNITS not in options:
            options[CONF_UNITS] = hass.config.units.name

        if CONF_TRAVEL_MODE in new_data:
            wstr = (
                "Google Travel Time: travel_mode is deprecated, please "
                "add mode to the options dictionary instead!"
            )
            _LOGGER.warning(wstr)
            travel_mode = new_data.pop(CONF_TRAVEL_MODE)
            if CONF_MODE not in options:
                options[CONF_MODE] = travel_mode

        if CONF_MODE not in options:
            options[CONF_MODE] = "driving"

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=options
        )

    api_key = config_entry.data[CONF_API_KEY]
    origin = config_entry.data[CONF_ORIGIN]
    destination = config_entry.data[CONF_DESTINATION]
    name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)

    client = Client(api_key, timeout=10)

    sensor = GoogleTravelTimeSensor(
        config_entry, name, api_key, origin, destination, client
    )

    async_add_entities([sensor], False)


class GoogleTravelTimeSensor(SensorEntity):
    """Representation of a Google travel time sensor."""

    def __init__(self, config_entry, name, api_key, origin, destination, client):
        """Initialize the sensor."""
        self._name = name
        self._config_entry = config_entry
        self._unit_of_measurement = TIME_MINUTES
        self._matrix = None
        self._api_key = api_key
        self._unique_id = config_entry.entry_id
        self._client = client

        # Check if location is a trackable entity
        if origin.split(".", 1)[0] in TRACKABLE_DOMAINS:
            self._origin_entity_id = origin
        else:
            self._origin = origin

        if destination.split(".", 1)[0] in TRACKABLE_DOMAINS:
            self._destination_entity_id = destination
        else:
            self._destination = destination

    async def async_added_to_hass(self) -> None:
        """Handle when entity is added."""
        if self.hass.state != CoreState.running:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self.first_update
            )
        else:
            await self.first_update()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._matrix is None:
            return None

        _data = self._matrix["rows"][0]["elements"][0]
        if "duration_in_traffic" in _data:
            return round(_data["duration_in_traffic"]["value"] / 60)
        if "duration" in _data:
            return round(_data["duration"]["value"] / 60)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._api_key)},
            name=DOMAIN,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID of entity."""
        return self._unique_id

    @property
    def name(self):
        """Get the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._matrix is None:
            return None

        res = self._matrix.copy()
        options = self._config_entry.options.copy()
        res.update(options)
        del res["rows"]
        _data = self._matrix["rows"][0]["elements"][0]
        if "duration_in_traffic" in _data:
            res["duration_in_traffic"] = _data["duration_in_traffic"]["text"]
        if "duration" in _data:
            res["duration"] = _data["duration"]["text"]
        if "distance" in _data:
            res["distance"] = _data["distance"]["text"]
        res["origin"] = self._origin
        res["destination"] = self._destination
        res[ATTR_ATTRIBUTION] = ATTRIBUTION
        return res

    @property
    def native_unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    async def first_update(self, _=None):
        """Run the first update and write the state."""
        await self.hass.async_add_executor_job(self.update)
        self.async_write_ha_state()

    def update(self):
        """Get the latest data from Google."""
        options_copy = self._config_entry.options.copy()
        dtime = options_copy.get(CONF_DEPARTURE_TIME)
        atime = options_copy.get(CONF_ARRIVAL_TIME)
        if dtime is not None and ":" in dtime:
            options_copy[CONF_DEPARTURE_TIME] = convert_time_to_utc(dtime)
        elif dtime is not None:
            options_copy[CONF_DEPARTURE_TIME] = dtime
        elif atime is None:
            options_copy[CONF_DEPARTURE_TIME] = "now"

        if atime is not None and ":" in atime:
            options_copy[CONF_ARRIVAL_TIME] = convert_time_to_utc(atime)
        elif atime is not None:
            options_copy[CONF_ARRIVAL_TIME] = atime

        # Convert device_trackers to google friendly location
        if hasattr(self, "_origin_entity_id"):
            self._origin = find_coordinates(self.hass, self._origin_entity_id)

        if hasattr(self, "_destination_entity_id"):
            self._destination = find_coordinates(self.hass, self._destination_entity_id)

        if self._destination is not None and self._origin is not None:
            self._matrix = distance_matrix(
                self._client, self._origin, self._destination, **options_copy
            )
