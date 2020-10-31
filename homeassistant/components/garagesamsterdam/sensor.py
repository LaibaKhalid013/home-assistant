"""Sensor platform for Garages Amsterdam."""
import logging

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinator
from .const import ATTRIBUTION

SENSORS = {
    "freeSpaceShort": "mdi:car",
    "freeSpaceLong": "mdi:car",
    "shortCapacity": "mdi:car",
    "longCapacity": "mdi:car",
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer sensor setup to the shared sensor module."""
    coordinator = await get_coordinator(hass)

    async_add_entities(
        GaragesamsterdamSensor(coordinator, config_entry.data["garageName"], info_type)
        for info_type in SENSORS
    )
    # _LOGGER.error("Entity value: %s", config_entry.data)


class GaragesamsterdamSensor(CoordinatorEntity):
    """Sensor representing garages amsterdam data."""

    name = None
    unique_id = None

    def __init__(self, coordinator, garageName, info_type):
        """Initialize garages amsterdam sensor."""
        super().__init__(coordinator)
        self.name = f"{coordinator.data[garageName].garageName[3:]} - {info_type}"
        self.unique_id = f"{garageName[3:]}-{info_type}"
        self.garageName = garageName
        self.info_type = info_type

        _LOGGER.error(
            "Inside INIT value: %s %s",
            self.info_type,
            getattr(self.coordinator.data[self.garageName], self.info_type),
        )

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success and (
            self.garageName in self.coordinator.data
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        _LOGGER.error(
            "Inside ENABLED value: %s %s",
            self.info_type,
            getattr(self.coordinator.data[self.garageName], self.info_type),
        )
        if getattr(self.coordinator.data[self.garageName], self.info_type) == "0":
            return False

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.error(
            "Inside STATE value: %s",
            getattr(self.coordinator.data[self.garageName], self.info_type),
        )
        return getattr(self.coordinator.data[self.garageName], self.info_type)

    @property
    def icon(self):
        """Return the icon."""
        return SENSORS[self.info_type]

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return "cars"

    @property
    def device_state_attributes(self):
        """Return device attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    # @property
    # def entity_registry_enabled_default(self) -> bool:
    #     """Disable entity if freeSpaceLong or capacityLong has no value / None"""
    #     if getattr(self.coordinator.data[self.garageName], self.info_type) is None:
    #         return False
