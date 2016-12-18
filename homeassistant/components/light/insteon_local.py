"""
Support for Insteon local lights.

For more details about this platform, please refer to the documentation at

--
Example platform config
--

insteon_local:
  host: YOUR HUB IP
  username: YOUR HUB USERNAME
  password: YOUR HUB PASSWORD

--
Example platform config
--

light:
  - platform: insteon_local
    lights:
      dining_room:
        device_id: 30DA8A
        name: Dining Room
      living_room:
        device_id: 30D927
        name: Living Room

"""

from homeassistant.components.light import (ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS, Light)
import homeassistant.util as util
from time import sleep
from datetime import timedelta


DEPENDENCIES = ['insteon_local']

SUPPORT_INSTEON_LOCAL = SUPPORT_BRIGHTNESS

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(milliseconds=100)

DOMAIN = "light"


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Insteon local light platform."""

    INSTEON_LOCAL = hass.data['insteon_local']
    devs = []
    if len(config) > 0:
        items = config['lights'].items()

        # todo: use getLinked instead
        for key, light in items:
            device = INSTEON_LOCAL.dimmer(light['device_id'])
            device.beep()
            devs.append(InsteonLocalDimmerDevice(device, light['name']))
        add_devices(devs)


class InsteonLocalDimmerDevice(Light):
    """An abstract Class for an Insteon node."""

    def __init__(self, node, name):
        """Initialize the device."""
        self.node = node
        self.node.deviceName = name
        self._value = 0

    @property
    def name(self):
        """Return the the name of the node."""

        return self.node.deviceName

    @property
    def unique_id(self):
        """Return the ID of this insteon node."""
        return self.node.deviceId

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._value

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Update state of the sensor."""
        id = self.node.deviceId.upper()
        self.node.hub.directCommand(id, '19', '00')
        resp = self.node.hub.getBufferStatus(id)
        attempts = 1
        while 'cmd2' not in resp and attempts < 9:
            if attempts % 3 == 0:
                self.node.hub.directCommand(id, '19', '00')
            else:
                sleep(1)
            resp = self.node.hub.getBufferStatus(id)
            attempts += 1

        if 'cmd2' in resp:
            self._value = int(resp['cmd2'], 16)

    @property
    def is_on(self):
        """Return the boolean response if the node is on."""
        return self._value != 0

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_INSTEON_LOCAL

    def turn_on(self, **kwargs):
        brightness = 100
        """Turn device on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS] / 255 * 100

        self.node.on(brightness)

    def turn_off(self, **kwargs):
        """Turn device off."""
        self.node.offInstant()
