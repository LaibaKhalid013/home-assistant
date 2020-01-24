"""Support for Velbus sensors."""
import logging

from homeassistant.const import DEVICE_CLASS_POWER, ENERGY_KILO_WATT_HOUR

from . import VelbusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Velbus sensor based on config_entry."""
    cntrl = hass.data[DOMAIN][entry.entry_id]["cntrl"]
    modules_data = hass.data[DOMAIN][entry.entry_id]["sensor"]
    entities = []
    for address, channel in modules_data:
        module = cntrl.get_module(address)
        entities.append(VelbusSensor(module, channel))
        if module.get_class(channel) == "counter":
            entities.append(VelbusSensor(module, channel, True))
    async_add_entities(entities)


class VelbusSensor(VelbusEntity):
    """Representation of a sensor."""

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self._module.get_class(self._channel) == "counter" and not self._is_counter:
            if self._module.get_counter_unit(self._channel) == ENERGY_KILO_WATT_HOUR:
                return DEVICE_CLASS_POWER
            else:
                return None
        return self._module.get_class(self._channel)

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._is_counter:
            return self._module.get_counter_state(self._channel)
        else:
            return self._module.get_state(self._channel)

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        if self._is_counter:
            return self._module.get_counter_unit(self._channel)
        else:
            return self._module.get_unit(self._channel)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        if self._is_counter:
            return "mdi:counter"
        return None
