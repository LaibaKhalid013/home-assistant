"""
Support for KNX/IP switches via XKNX

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.xknx/
"""
import asyncio
import xknx
import voluptuous as vol

from homeassistant.components.xknx import DATA_XKNX
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchDevice
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv

CONF_ADDRESS = 'address'
CONF_STATE_ADDRESS = 'state_address'

DEFAULT_NAME = 'XKNX Switch'
DEPENDENCIES = ['xknx']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_STATE_ADDRESS): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, \
        discovery_info=None):
    """Set up switch(es) for XKNX platform."""
    if DATA_XKNX not in hass.data \
            or not hass.data[DATA_XKNX].initialized:
        return False

    if discovery_info is not None:
        yield from add_devices_from_component(hass, add_devices)
    else:
        yield from add_devices_from_platform(hass, config, add_devices)

    return True

@asyncio.coroutine
def add_devices_from_component(hass, add_devices):
    """Set up switches for XKNX platform configured via xknx.yaml."""
    entities = []
    for device in hass.data[DATA_XKNX].xknx.devices:
        if isinstance(device, xknx.Switch) and \
			    not hasattr(device, "already_added_to_hass"):
            entities.append(XKNXSwitch(hass, device))
    add_devices(entities)

@asyncio.coroutine
def add_devices_from_platform(hass, config, add_devices):
    """Set up switch for XKNX platform configured within plattform."""
    from xknx import Switch
    switch = Switch(hass.data[DATA_XKNX].xknx,
                    name= \
                        config.get(CONF_NAME),
                    group_address= \
                        config.get(CONF_ADDRESS),
                    group_address_state= \
                        config.get(CONF_STATE_ADDRESS))
    switch.already_added_to_hass = True
    hass.data[DATA_XKNX].xknx.devices.add(switch)
    add_devices([XKNXSwitch(hass, switch)])


class XKNXSwitch(SwitchDevice):
    """Representation of a XKNX switch."""

    def __init__(self, hass, device):
        self.device = device
        self.hass = hass
        self.register_callbacks()

    def register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        def after_update_callback(device):
            # pylint: disable=unused-argument
            self.update_ha_state()
        self.device.register_device_updated_cb(after_update_callback)

    @property
    def name(self):
        """Return the name of the XKNX device."""
        return self.device.name

    @property
    def should_poll(self):
        """No polling needed within XKNX."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.device.state

    def turn_on(self):
        """Turn the device on."""
        self.device.set_on()

    def turn_off(self):
        """Turn the device off."""
        self.device.set_off()
