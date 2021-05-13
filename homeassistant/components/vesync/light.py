"""Support for VeSync bulbs and wall dimmers."""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_COLOR_TEMP,
    LightEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .common import VeSyncDevice
from .const import DOMAIN, VS_DISCOVERY, VS_DISPATCHERS, VS_LIGHTS

_LOGGER = logging.getLogger(__name__)

DEV_TYPE_TO_HA = {
    "ESD16": "walldimmer",
    "ESWD16": "walldimmer",
    "ESL100": "bulb-dimmable",
    "ESL100CW": "bulb-tunable-white",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up lights."""

    async def async_discover(devices):
        """Add new devices to platform."""
        _async_setup_entities(devices, async_add_entities)

    disp = async_dispatcher_connect(
        hass, VS_DISCOVERY.format(VS_LIGHTS), async_discover
    )
    hass.data[DOMAIN][VS_DISPATCHERS].append(disp)

    _async_setup_entities(hass.data[DOMAIN][VS_LIGHTS], async_add_entities)


@callback
def _async_setup_entities(devices, async_add_entities):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        if DEV_TYPE_TO_HA.get(dev.device_type) in ("walldimmer", "bulb-dimmable"):
            entities.append(VeSyncDimmableLightHA(dev))
        elif DEV_TYPE_TO_HA.get(dev.device_type) in ("bulb-tunable-white"):
            entities.append(VeSyncTunableWhiteLightHA(dev))
        else:
            _LOGGER.debug(
                "%s - Unknown device type - %s", dev.device_name, dev.device_type
            )
            continue

    async_add_entities(entities, update_before_add=True)


class VeSyncBaseLight(VeSyncDevice, LightEntity):
    """Base class for VeSync Light Devices Representations."""

    def __init__(self, device):
        """Initialize the VeSync LightDevice."""
        super().__init__(device)
        self.device = device

    @property
    def brightness(self):
        """Get light brightness."""
        # get value from pyvesync library api,
        r = self.device.brightness
        try:
            # check for validity of brightness value received
            brightness_value = int(r)
            # convert percent brightness to ha expected range
            brightness_value = round((max(1, brightness_value) / 100) * 255)
            return brightness_value
        except ValueError:
            # deal if any unexpected value
            _LOGGER.debug(
                "VeSync - received brightness level from pyvesync api out of range: %d",
                brightness_value,
            )
            return 0

    def turn_on(self, **kwargs):
        """Turn the device on."""
        # set brightness level
        if self.color_mode in (COLOR_MODE_BRIGHTNESS, COLOR_MODE_COLOR_TEMP):
            if ATTR_BRIGHTNESS in kwargs:
                # get brightness from HA data
                brightness = int(kwargs[ATTR_BRIGHTNESS])
                # convert to percent that vesync api expects
                brightness = round((max(1, brightness) / 255) * 100)
                # ensure value between 0-100
                brightness = max(1, min(brightness, 100))
                self.device.set_brightness(brightness)
                return
        # set white temperature
        if self.color_mode in (COLOR_MODE_COLOR_TEMP):
            if ATTR_COLOR_TEMP in kwargs:
                # get white temperature from HA data
                color_temp = int(kwargs[ATTR_COLOR_TEMP])
                # convert Mireds to Percent value that api expects
                color_temp = round(
                    (
                        (color_temp - self.min_mireds)
                        / (self.max_mireds - self.min_mireds)
                    )
                    * 100
                )
                # flip cold/warm to what pyvesync api expects
                color_temp = 100 - color_temp
                # ensure value between 0-100
                color_temp = max(0, min(color_temp, 100))
                # pass value to pyvesync library api
                self.device.set_color_temp(color_temp)
                return
        # send turn_on command to pyvesync api
        self.device.turn_on()


class VeSyncDimmableLightHA(VeSyncBaseLight, LightEntity):
    """Representation of a VeSync dimmable light device."""

    def __init__(self, device):
        """Initialize the VeSync dimmable light device."""
        super().__init__(device)
        self.device = device

    @property
    def color_mode(self):
        """Set color mode for this entity."""
        return COLOR_MODE_BRIGHTNESS

    @property
    def supported_color_modes(self):
        """Flag supported color_modes (in an array format)."""
        return [COLOR_MODE_BRIGHTNESS]


class VeSyncTunableWhiteLightHA(VeSyncBaseLight, LightEntity):
    """Representation of a VeSync Tunable White Light device."""

    def __init__(self, device):
        """Initialize the VeSync Tunable White Light device."""
        super().__init__(device)
        self.device = device

    @property
    def color_temp(self):
        """Get device white temperature."""
        # get value from pyvesync library api,
        color_temp_value = int(self.device.color_temp_pct)
        # flip cold/warm
        color_temp_value = 100 - color_temp_value
        # ensure value between 0-100
        color_temp_value = max(0, min(color_temp_value, 100))
        # convert percent value to Mireds
        color_temp_value = round(
            self.min_mireds
            + ((self.max_mireds - self.min_mireds) / 100 * color_temp_value)
        )
        # ensure value between minimum and maximum Mireds
        color_temp_value = max(self.min_mireds, min(color_temp_value, self.max_mireds))
        return color_temp_value

    @property
    def min_mireds(self):
        """Set device coldest white temperature."""
        return 154  # 154 Mireds ( 1,000,000 divided by 6500 Kelvin = 154 Mireds)

    @property
    def max_mireds(self):
        """Set device warmest white temperature."""
        return 370  # 370 Mireds  ( 1,000,000 divided by 2700 Kelvin = 370 Mireds)

    @property
    def color_mode(self):
        """Set color mode for this entity."""
        return COLOR_MODE_COLOR_TEMP

    @property
    def supported_color_modes(self):
        """Flag supported color_modes (in an array format)."""
        return [COLOR_MODE_COLOR_TEMP]
