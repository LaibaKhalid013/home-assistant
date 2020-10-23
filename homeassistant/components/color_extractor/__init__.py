"""Module for color_extractor (RGB extraction from images) component."""
import asyncio
import io
import logging

from PIL import UnidentifiedImageError
import aiohttp
import async_timeout
from colorthief import ColorThief
import voluptuous as vol

from homeassistant.components.color_extractor.const import (
    ATTR_PATH,
    ATTR_URL,
    DOMAIN,
    SERVICE_PREDOMINANT_COLOR_FILE,
    SERVICE_PREDOMINANT_COLOR_URL,
)
from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    LIGHT_TURN_ON_SCHEMA,
    SERVICE_TURN_ON,
)
from homeassistant.helpers import aiohttp_client
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Extend the existing light.turn_on service schema
SERVICE_SCHEMA = cv.make_entity_service_schema(
    {
        **LIGHT_TURN_ON_SCHEMA,
        vol.Exclusive(ATTR_PATH, "color_extractor"): cv.isfile,
        vol.Exclusive(ATTR_URL, "color_extractor"): cv.url,
    }
)


def _get_file(file_path):
    """Get a PIL acceptable input file reference.

    Allows us to mock patch during testing to make BytesIO stream.
    """
    return file_path


async def async_setup(hass, hass_config):
    """Set up services for color_extractor integration."""

    def _get_color(file_handler) -> tuple:
        """Given an image file, extract the predominant color from it."""
        try:
            color_thief = ColorThief(file_handler)
        except UnidentifiedImageError as ex:
            _LOGGER.error("Bad image file provided, are you sure it's an image? %s", ex)
            return

        # get_color returns a SINGLE RGB value for the given image
        color = color_thief.get_color(quality=1)

        _LOGGER.debug("Extracted RGB color %s from image", color)

        return color

    async def async_predominant_color_url_service(service_call):
        """Handle call for URL based image."""
        service_data = dict(service_call.data)

        url = service_data.pop(ATTR_URL)

        if not hass.config.is_allowed_external_url(url):
            _LOGGER.error(
                "External URL '%s' is not allowed, please add to 'allowlist_external_urls'",
                url,
            )
            return

        _LOGGER.debug("Getting predominant RGB from image URL '%s'", url)

        # Download the image into a buffer for ColorThief to check against
        try:
            session = aiohttp_client.async_get_clientsession(hass)

            with async_timeout.timeout(10):
                response = await session.get(url)

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to get ColorThief image due to HTTPError: %s", err)
            return

        content = await response.content.read()

        with io.BytesIO(content) as _file:
            _file.name = "color_extractor.jpg"
            _file.seek(0)

            color = _get_color(_file)

        if color:
            service_data[ATTR_RGB_COLOR] = color

            await hass.services.async_call(
                LIGHT_DOMAIN, SERVICE_TURN_ON, service_data, blocking=True
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PREDOMINANT_COLOR_URL,
        async_predominant_color_url_service,
        schema=SERVICE_SCHEMA,
    )

    async def async_predominant_color_file_service(service_call):
        """Handle call for local file based image."""
        service_data = dict(service_call.data)

        file_path = service_data.pop(ATTR_PATH)

        if not hass.config.is_allowed_path(file_path):
            _LOGGER.error(
                "File path '%s' is not allowed, please add to 'allowlist_external_dirs'",
                file_path,
            )
            return

        _LOGGER.debug("Getting predominant RGB from file path '%s'", file_path)

        _file = _get_file(file_path)
        color = _get_color(_file)

        if color:
            service_data[ATTR_RGB_COLOR] = color

            await hass.services.async_call(
                LIGHT_DOMAIN, SERVICE_TURN_ON, service_data, blocking=True
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PREDOMINANT_COLOR_FILE,
        async_predominant_color_file_service,
        schema=SERVICE_SCHEMA,
    )

    return True
