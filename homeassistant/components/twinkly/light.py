"""The Twinkly light component."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError
from awesomeversion import AwesomeVersion
from ttls.client import Twinkly
from ttls.colours import TwinklyColour

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_SW_VERSION, CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import color_rgb_to_rgbw, color_rgbw_to_rgb

from .const import (
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    DATA_CLIENT,
    DATA_DEVICE_INFO,
    DEV_LED_PROFILE,
    DEV_MODEL,
    DEV_NAME,
    DEV_PROFILE_RGB,
    DEV_PROFILE_RGBW,
    DOMAIN,
    MIN_EFFECT_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setups an entity from a config entry (UI config flow)."""

    client = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]
    device_info = hass.data[DOMAIN][config_entry.entry_id][DATA_DEVICE_INFO]
    software_version = hass.data[DOMAIN][config_entry.entry_id][ATTR_SW_VERSION]

    entity = TwinklyLight(config_entry, client, device_info, software_version)

    async_add_entities([entity], update_before_add=True)


class TwinklyLight(LightEntity):
    """Implementation of the light for the Twinkly service."""

    _attr_icon = "mdi:string-lights"

    def __init__(
        self,
        conf: ConfigEntry,
        client: Twinkly,
        device_info,
        software_version: str | None = None,
    ) -> None:
        """Initialize a TwinklyLight entity."""
        self._attr_unique_id: str = conf.data[CONF_ID]
        self._conf = conf

        if device_info.get(DEV_LED_PROFILE) == DEV_PROFILE_RGBW:
            self._attr_supported_color_modes = {ColorMode.RGBW}
            self._attr_color_mode = ColorMode.RGBW
            self._attr_rgbw_color = (255, 255, 255, 0)
        elif device_info.get(DEV_LED_PROFILE) == DEV_PROFILE_RGB:
            self._attr_supported_color_modes = {ColorMode.RGB}
            self._attr_color_mode = ColorMode.RGB
            self._attr_rgb_color = (255, 255, 255)
        else:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS

        # Those are saved in the config entry in order to have meaningful values even
        # if the device is currently offline.
        # They are expected to be updated using the device_info.
        self._name = conf.data[CONF_NAME]
        self._model = conf.data[CONF_MODEL]

        self._client = client

        # Set default state before any update
        self._attr_is_on = False
        self._attr_available = False
        self._current_movie: dict[Any, Any] = {}
        self._movies: list[Any] = []
        self._software_version = software_version
        # We guess that most devices are "new" and support effects
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_last_mode: str | None = None

    @property
    def name(self) -> str:
        """Name of the device."""
        return self._name if self._name else "Twinkly light"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Get device specific attributes."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="LEDWORKS",
            model=self._model,
            name=self.name,
            sw_version=self._software_version,
        )

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if "name" in self._current_movie:
            return f"{self._current_movie['id']} {self._current_movie['name']}"
        return None

    @property
    def effect_list(self) -> list[str]:
        """Return the list of saved effects."""
        effect_list = []
        for movie in self._movies:
            effect_list.append(f"{movie['id']} {movie['name']}")
        return effect_list

    async def async_added_to_hass(self) -> None:
        """Device is added to hass."""
        if self._software_version:
            if AwesomeVersion(self._software_version) < AwesomeVersion(
                MIN_EFFECT_VERSION
            ):
                self._attr_supported_features = (
                    self.supported_features & ~LightEntityFeature.EFFECT
                )
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get_device(
                {(DOMAIN, self._attr_unique_id)}, set()
            )
            if device_entry:
                device_registry.async_update_device(
                    device_entry.id, sw_version=self._software_version
                )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(int(kwargs[ATTR_BRIGHTNESS]) / 2.55)

            # If brightness is 0, the twinkly will only "disable" the brightness,
            # which means that it will be 100%.
            if brightness == 0:
                await self._client.turn_off()
                return

            await self._client.set_brightness(brightness)

        await self._client.interview()
        color = None
        if (
            ATTR_RGBW_COLOR in kwargs
            and kwargs[ATTR_RGBW_COLOR] != self._attr_rgbw_color
        ):
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
            color = TwinklyColour(r, g, b, w)
            self._attr_rgbw_color = kwargs[ATTR_RGBW_COLOR]
        elif (
            ATTR_RGB_COLOR in kwargs and kwargs[ATTR_RGB_COLOR] != self._attr_rgb_color
        ):
            r, g, b = kwargs[ATTR_RGB_COLOR]
            color = TwinklyColour(r, g, b)
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
        if color:
            _LOGGER.warning("Setting color to %s", color)
            _LOGGER.warning(self._attr_supported_color_modes)
            if self._attr_color_mode == ColorMode.RGBW:
                if color.white is None:
                    rgbw_color = color_rgb_to_rgbw(color.red, color.green, color.blue)
                    r, g, b, w = rgbw_color
                    color = TwinklyColour(r, g, b, w)
                _LOGGER.warning("Really setting rgbw color to %s", color)
            elif self._attr_color_mode == ColorMode.RGB:
                if color.white:
                    rgb_color = color_rgbw_to_rgb(
                        color.red, color.green, color.blue, color.white
                    )
                    r, g, b = rgb_color
                    color = TwinklyColour(r, g, b)
                _LOGGER.warning("Really setting rgb color to %s", color)
            if LightEntityFeature.EFFECT & self.supported_features:
                await self._client.set_static_colour(color)
                await self._client.set_mode("color")
                self._client.default_mode = "color"
                self._attr_last_mode = "color"
            else:
                await self._client.set_cycle_colours(color)
                await self._client.set_mode("movie")
                self._client.default_mode = "movie"
                self._attr_last_mode = "movie"

        if (
            ATTR_EFFECT in kwargs
            and LightEntityFeature.EFFECT & self.supported_features
        ):
            movie_id = kwargs[ATTR_EFFECT].split(" ")[0]
            if "id" not in self._current_movie or int(movie_id) != int(
                self._current_movie["id"]
            ):
                await self._client.set_current_movie(int(movie_id))
                await self._client.set_mode("movie")
                self._client.default_mode = "movie"
                self._attr_last_mode = "movie"
        if not self._attr_is_on:
            await self._client.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        await self._client.turn_off()

    async def async_update(self) -> None:
        """Asynchronously updates the device properties."""
        _LOGGER.debug("Updating '%s'", self._client.host)

        try:
            await self._client.interview()
            self._attr_is_on = await self._client.is_on()

            brightness = await self._client.get_brightness()
            brightness_value = (
                int(brightness["value"]) if brightness["mode"] == "enabled" else 100
            )

            self._attr_brightness = (
                int(round(brightness_value * 2.55)) if self._attr_is_on else 0
            )

            device_info = await self._client.get_details()

            if (
                DEV_NAME in device_info
                and DEV_MODEL in device_info
                and (
                    device_info[DEV_NAME] != self._name
                    or device_info[DEV_MODEL] != self._model
                )
            ):
                self._name = device_info[DEV_NAME]
                self._model = device_info[DEV_MODEL]

                # If the name has changed, persist it in conf entry,
                # so we will be able to restore this new name if hass
                # is started while the LED string is offline.
                self.hass.config_entries.async_update_entry(
                    self._conf,
                    data={
                        CONF_HOST: self._client.host,  # this cannot change
                        CONF_ID: self._attr_unique_id,  # this cannot change
                        CONF_NAME: self._name,
                        CONF_MODEL: self._model,
                    },
                )

            await self.async_update_current_color()
            if LightEntityFeature.EFFECT & self.supported_features:
                await self.async_update_movies()
                await self.async_update_current_movie()

            if not self._attr_available:
                _LOGGER.info("Twinkly '%s' is now available", self._client.host)

            # _LOGGER.debug("Current details: %s", await self._client.summary())
            # _LOGGER.debug("Current mode: %s", await self._client.get_mode())
            # _LOGGER.debug("Current default mode: %s", self._client.default_mode)

            # We don't use the echo API to track the availability since
            # we already have to pull the device to get its state.
            self._attr_available = True
        except (asyncio.TimeoutError, ClientError):
            # We log this as "info" as it's pretty common that the Christmas
            # light are not reachable in July
            if self._attr_available:
                _LOGGER.info(
                    "Twinkly '%s' is not reachable (client error)", self._client.host
                )
            self._attr_available = False

    async def async_update_movies(self) -> None:
        """Update the list of movies (effects)."""
        movies = await self._client.get_saved_movies()
        _LOGGER.debug("Movies: %s", movies)
        if movies and "movies" in movies:
            self._movies = movies["movies"]

    async def async_update_current_movie(self) -> None:
        """Update the current active movie."""
        current_movie = await self._client.get_current_movie()
        _LOGGER.debug("Current movie: %s", current_movie)
        if current_movie and "id" in current_movie:
            self._current_movie = current_movie

    async def async_update_current_color(self) -> None:
        """Update the current active color."""
        current_color = await self._client.get_current_colour()
        if "white" in current_color:
            color = TwinklyColour(
                current_color["red"],
                current_color["green"],
                current_color["blue"],
                current_color["white"],
            )
        else:
            color = TwinklyColour(
                current_color["red"], current_color["green"], current_color["blue"]
            )
        _LOGGER.debug("Current color: %s", color)
        if self._attr_color_mode == ColorMode.RGBW:
            if color.white:
                self._attr_rgbw_color = (
                    color.red,
                    color.green,
                    color.blue,
                    color.white,
                )
            else:
                self._attr_rgbw_color = color_rgb_to_rgbw(
                    color.red,
                    color.green,
                    color.blue,
                )
        elif self._attr_color_mode == ColorMode.RGB:
            if color.white:
                self._attr_rgb_color = color_rgbw_to_rgb(
                    color.red,
                    color.green,
                    color.blue,
                    color.white,
                )
            else:
                self._attr_rgb_color = (
                    color.red,
                    color.green,
                    color.blue,
                )
