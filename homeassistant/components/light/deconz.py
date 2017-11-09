"""Platform integrating Deconz light support.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/light/deconz/
"""

import asyncio
import logging

from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)
from homeassistant.core import callback
from homeassistant.components.deconz import DATA_DECONZ

DEPENDENCIES = ['deconz']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Setup light platform for Deconz."""
    if DATA_DECONZ in hass.data:
        lights = hass.data[DATA_DECONZ].lights
        groups = hass.data[DATA_DECONZ].groups

    for _, light in lights.items():
        async_add_devices([DeconzLight(light)], True)

    for _, group in groups.items():
        if group.lights:
            async_add_devices([DeconzLight(group)], True)


class DeconzLight(Light):
    """Deconz light representation.

    Only supports dimmable lights at the moment.
    """

    def __init__(self, light):
        """Setup light and add update callback to get data from websocket."""
        self._state = light.state
        self._brightness = light.brightness
        self._light = light
        self._light.register_callback(self._update_callback)

    @callback
    def _update_callback(self):
        """Update the sensor's state, if needed."""
        self._state = self._light.state
        self._brightness = self._light.brightness
        self.async_schedule_update_ha_state()

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def name(self):
        """Return the name of the event."""
        return self._light.name

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn on light."""
        data = {'on': True}
        if ATTR_BRIGHTNESS in kwargs:
            data['bri'] = kwargs[ATTR_BRIGHTNESS]
        yield from self._light.set_state(data)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Turn off light."""
        data = {'on': False}
        yield from self._light.set_state(data)

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        if self._light.type != 'LightGroup':
            attr = {
                'manufacturer': self._light.manufacturer,
                'modelid': self._light.modelid,
                'reachable': self._light.reachable,
                'swversion': self._light.swversion,
                'uniqueid': self._light.uniqueid,
            }
            return attr
