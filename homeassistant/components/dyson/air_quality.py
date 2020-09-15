"""Support for Dyson Pure Cool Air Quality Sensors."""
import logging

from libpurecool.dyson_pure_cool import DysonPureCool
from libpurecool.dyson_pure_state_v2 import DysonEnvironmentalSensorV2State

from homeassistant.components.air_quality import AirQualityEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN

ATTRIBUTION = "Dyson purifier air quality sensor"

_LOGGER = logging.getLogger(__name__)

ATTR_VOC = "volatile_organic_compounds"


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up the Dyson Sensors."""
    # Get Dyson Devices from parent component
    entities = []
    for device in hass.data[DOMAIN][config_entry.entry_id]:
        if isinstance(device, DysonPureCool):
            entities.append(DysonAirSensor(device))
    async_add_entities(entities)


class DysonAirSensor(AirQualityEntity):
    """Representation of a generic Dyson air quality sensor."""

    def __init__(self, device):
        """Create a new generic air quality Dyson sensor."""
        self._device = device
        self._old_value = None
        self._name = device.name

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        self.hass.async_add_executor_job(
            self._device.add_message_listener, self.on_message
        )

    def on_message(self, message):
        """Handle new messages which are received from the fan."""
        _LOGGER.debug(
            "air_quality: Message received for %s device: %s", self.name, message
        )
        if (
            self._old_value is None
            or self._old_value != self._device.environmental_state
        ) and isinstance(message, DysonEnvironmentalSensorV2State):
            self._old_value = self._device.environmental_state
            self.schedule_update_ha_state()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the Dyson sensor."""
        return self._name

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        return max(
            self.particulate_matter_2_5,
            self.particulate_matter_10,
            self.nitrogen_dioxide,
            self.volatile_organic_compounds,
        )

    @property
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.particulate_matter_25)
        return None

    @property
    def particulate_matter_10(self):
        """Return the particulate matter 10 level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.particulate_matter_10)
        return None

    @property
    def nitrogen_dioxide(self):
        """Return the NO2 (nitrogen dioxide) level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.nitrogen_dioxide)
        return None

    @property
    def volatile_organic_compounds(self):
        """Return the VOC (Volatile Organic Compounds) level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.volatile_organic_compounds)
        return None

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return self._device.serial

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        data = {}

        voc = self.volatile_organic_compounds
        if voc is not None:
            data[ATTR_VOC] = voc
        return data
