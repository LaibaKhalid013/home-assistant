"""Base classe for tankerkoenig sensor integration."""
import logging

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_CLOSED,
    STATE_OPEN,
)
from homeassistant.helpers.entity import Entity

from .const import NAME

_LOGGER = logging.getLogger(__name__)

ATTR_ADDRESS = "address"
ATTR_BRAND = "brand"
ATTR_FUEL_TYPE = "fuel_type"
ATTR_IS_OPEN = "state"
ATTR_STATION_NAME = "station_name"
ATTRIBUTION = "Data provided by https://creativecommons.tankerkoenig.de"

ICON = "mdi:fuel"


class FuelPriceSensorBase(Entity):
    """Contains prices for fuels in the given station."""

    def __init__(self, fuel_type, station, name=NAME):
        """Initialize the sensor."""
        self._data = None
        self._station = station
        self._station_id = station["id"]
        self._fuel_type = fuel_type
        self._name = name
        self._latitude = station["lat"]
        self._longitude = station["lng"]
        self._is_open = STATE_OPEN if station["isOpen"] else STATE_CLOSED
        self._address = f"{station['street']} {station['houseNumber']}, {station['postCode']} {station['place']}"
        _LOGGER.debug("Setup standalone sensor %s", name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return "€"

    @property
    def state(self):
        """Return the state of the device."""
        if self._data is None or self._fuel_type not in self._data.keys():
            return self._station[self._fuel_type]
        return self._data[self._fuel_type]

    @property
    def device_state_attributes(self):
        """Return the attributes of the device."""
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_BRAND: self._station["brand"],
            ATTR_FUEL_TYPE: self._fuel_type,
            ATTR_STATION_NAME: self._station["name"],
            ATTR_ADDRESS: self._address,
            ATTR_LATITUDE: self._latitude,
            ATTR_LONGITUDE: self._longitude,
            ATTR_IS_OPEN: self._is_open,
        }
        return attrs

    def new_data(self, data):
        """Update the internal sensor data."""
        self._data = data
        self._is_open = STATE_OPEN if data["status"] == "open" else STATE_CLOSED
