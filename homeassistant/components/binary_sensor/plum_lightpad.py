"""
Support for Plum Lightpad switches.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/light.plum_lightpad
"""
import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.components.plum_lightpad import PLUM_DATA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

DEPENDENCIES = ['plum_lightpad']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


async def async_setup_platform(hass, config, add_devices,
                               discovery_info=None):
    """Set up the motion sensors for the Plum Lightpad  platform."""
    plum = hass.data[PLUM_DATA]

    @callback
    async def new_lightpad(lightpad):
        """Callback when a new lightpad is discovered."""
        add_devices([
            PlumMotionSensor(lightpad=lightpad, hass=hass),
        ])

    plum.add_lightpad_listener(new_lightpad)

    for lightpad in plum.lightpads.values():
        await new_lightpad(lightpad)


class PlumMotionSensor(BinarySensorDevice):
    """Representation of a Lightpad's motion detection."""

    def __init__(self, hass, lightpad):
        """Init Plum Motion Sensor."""
        self._hass = hass
        self._lightpad = lightpad
        self.off_delay = 10
        self._signal = None
        self._latest_motion = None

        lightpad.add_event_listener('pirSignal', self.motion_detected)

    def motion_detected(self, event):
        """Motion Detected handler."""
        self._signal = event['signal']
        self._latest_motion = dt_util.utcnow()
        self.schedule_update_ha_state()

        def off_handler(now):
            """Switch sensor off after a delay."""
            if (now - self._latest_motion).seconds >= self.off_delay:
                self._signal = None
                self.schedule_update_ha_state()

        async_call_later(hass=self.hass,
                         delay=self.off_delay, action=off_handler)

    @property
    def lpid(self):
        """Return the LightPad ID (lpid) which is attached to the sensor."""
        return self._lightpad.lpid

    @property
    def name(self):
        """Return the friendly name associated with the lightpad."""
        return self._lightpad.friendly_name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._signal is not None
