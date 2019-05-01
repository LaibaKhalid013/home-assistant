"""Support for an Intergas boiler attached to an Intouch Lan2RF gateway."""
import asyncio
import logging

from homeassistant.components.water_heater import WaterHeaterDevice
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

INTOUCH_SUPPORT_FLAGS = 0

INTOUCH_MAX_TEMP = 80.0
INTOUCH_MIN_TEMP = 30.0


async def async_setup_platform(hass, hass_config, async_add_entities,
                               discovery_info=None):
    """Set up an Intouch water_heater entity."""
    client = hass.data[DOMAIN]['client']

    # await client.update()
    water_heaters = await client.heaters

    async_add_entities([IntouchWaterHeater(client, water_heaters[0])],
                       update_before_add=True)


class IntouchWaterHeater(WaterHeaterDevice):
    """Representation of an InTouch water_heater device."""

    def __init__(self, client, boiler):
        """Initialize the water_heater device."""
        self._client = client
        self._objref = boiler
        self._name = 'Boiler'

    async def async_added_to_hass(self):
        """Set up a listener when this entity is added to HA."""
        async_dispatcher_connect(self.hass, DOMAIN, self._connect)

    @callback
    def _connect(self, packet):
        if packet['signal'] == 'refresh':
            self.async_schedule_update_ha_state(force_refresh=True)

    @property
    def name(self):
        """Return the name of the water_heater device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {'status': self._objref.status}

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._objref.heater_temp  # self._objref.tap_temp

    @property
    def min_temp(self):
        """Return max valid temperature that can be set."""
        return INTOUCH_MIN_TEMP

    @property
    def max_temp(self):
        """Return max valid temperature that can be set."""
        return INTOUCH_MAX_TEMP

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return INTOUCH_SUPPORT_FLAGS

    @property
    def state(self):
        """Return the current operation mode."""
        if self._objref.is_failed:
            return "Failed ({})".format(self._objref.fault_code)

        return self._objref.display_text

    @property
    def should_poll(self) -> bool:
        """Return False as this device should never be polled."""
        return False
