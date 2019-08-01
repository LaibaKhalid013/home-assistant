"""Support for Lutron switches."""
import logging

from homeassistant.components.switch import SwitchDevice

from . import LUTRON_CONTROLLER, LUTRON_DEVICES, LutronDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron switches."""
    devs = []
    for (area_name, device) in hass.data[LUTRON_DEVICES]["switch"]:
        dev = LutronSwitch(area_name, device, hass.data[LUTRON_CONTROLLER])
        devs.append(dev)

    add_entities(devs, True)


class LutronSwitch(LutronDevice, SwitchDevice):
    """Representation of a Lutron Switch."""

    def __init__(self, area_name, lutron_device, controller):
        """Initialize the switch."""
        self._is_on = False
        super().__init__(area_name, lutron_device, controller)

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._lutron_device.level = 100

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._lutron_device.level = 0

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        attr["lutron_integration_id"] = self._lutron_device.id
        return attr

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._lutron_device.last_level() > 0

    def update(self):
        """Call when forcing a refresh of the device."""
        self._is_on = self._lutron_device.level > 0
