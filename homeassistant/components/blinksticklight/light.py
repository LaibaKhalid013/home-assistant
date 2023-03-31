"""Support for Blinkstick lights."""
from __future__ import annotations

import logging
from typing import Any

from blinkstick import blinkstick
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.util.color as color_util

CONF_SERIAL = "serial"

CONF_NUM_LEDS = "num_leds"

DEFAULT_NAME = "Blinkstick"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SERIAL): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_NUM_LEDS, default=0): cv.positive_int,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Blinkstick device specified by serial number."""

    name = config[CONF_NAME]
    serial = config[CONF_SERIAL]
    num_leds = config[CONF_NUM_LEDS]

    stick = blinkstick.find_by_serial(serial)
    if stick:
        variant = stick.get_variant()

        if num_leds == 0:
            if variant == 3:  # BLINKSTICK_STRIP
                num_leds = 8
            elif variant == 4:  # BLINKSTICK_SQUARE
                num_leds = 8
            else:
                num_leds = 1

        logging.getLogger(__name__).debug(
            "blinkstick %s (variant %d) with %d leds detected",
            serial,
            variant,
            num_leds,
        )

        for index in range(num_leds):
            add_entities([BlinkStickLight(stick, name, index)], True)
    else:
        logging.getLogger(__name__).warning("No blinkstick detected")


class BlinkStickLight(LightEntity):
    """Representation of a BlinkStick light."""

    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}

    def __init__(self, stick, name, index):
        """Initialize the light."""
        self._stick = stick

        if index > 0:
            self._attr_name = name + " " + str(index)
        else:
            self._attr_name = name

        self._attr_led_index = index

    def update(self) -> None:
        """Read back the device state."""
        rgb_color = self._stick._get_color_rgb(index=self._attr_led_index)
        hsv = color_util.color_RGB_to_hsv(*rgb_color)
        self._attr_hs_color = hsv[:2]
        self._attr_brightness = int(hsv[2])
        self._attr_is_on = self.brightness is not None and self.brightness > 0

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]

        brightness: int = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._attr_brightness = brightness
        self._attr_is_on = bool(brightness)

        assert self.hs_color
        rgb_color = color_util.color_hsv_to_RGB(
            self.hs_color[0], self.hs_color[1], brightness / 255 * 100
        )
        self._stick.set_color(
            index=self._attr_led_index,
            red=rgb_color[0],
            green=rgb_color[1],
            blue=rgb_color[2],
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self._stick.set_color(index=self._attr_led_index, red=0, green=0, blue=0)
