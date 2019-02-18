"""Charge and Climate Control Support for the Nissan Leaf."""
import logging

from homeassistant.components.nissan_leaf import (
    DATA_CLIMATE, DATA_LEAF, LeafEntity)
from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['nissan_leaf']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Nissan Leaf switch platform setup."""
    devices = []
    for value in hass.data[DATA_LEAF].values():
        devices.append(LeafClimateSwitch(value))

    add_devices(devices, True)


class LeafClimateSwitch(LeafEntity, ToggleEntity):
    """Nissan Leaf Climate Control switch."""

    @property
    def name(self):
        """Switch name."""
        return "{} {}".format(self.car.leaf.nickname, "Climate Control")

    def log_registration(self):
        """Log registration."""
        _LOGGER.debug(
            "Registered LeafClimateSwitch component with HASS for VIN %s",
            self.car.leaf.vin)

    @property
    def device_state_attributes(self):
        """Return climate control attributes."""
        attrs = super().device_state_attributes
        attrs["updated_on"] = self.car.last_climate_response
        return attrs

    @property
    def is_on(self):
        """Return true if climate control is on."""
        return self.car.data[DATA_CLIMATE]

    async def async_turn_on(self, **kwargs):
        """Turn on climate control."""
        if await self.car.async_set_climate(True):
            self.car.data[DATA_CLIMATE] = True

    async def async_turn_off(self, **kwargs):
        """Turn off climate control."""
        if await self.car.async_set_climate(False):
            self.car.data[DATA_CLIMATE] = False

    # @MartinHjelmare would like removed - think provides nice UI feedback
    # for switch.
    # Think VolvoOnCall component hase different icons for the switches.
    @property
    def icon(self):
        """Climate control icon."""
        if self.car.data[DATA_CLIMATE]:
            return 'mdi:fan'
        return 'mdi:fan-off'
