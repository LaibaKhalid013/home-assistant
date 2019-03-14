"""Denon HEOS Media Player."""

import voluptuous as vol

from homeassistant.components.media_player.const import (
    DOMAIN as MEDIA_PLAYER_DOMAIN)
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

DOMAIN = 'heos'
REQUIREMENTS = ['aioheos==0.4.0']

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Set up the HEOS component."""
    from aioheos import AioHeosController

    host = config[DOMAIN][CONF_HOST]
    controller = AioHeosController(hass.loop, host)
    await controller.connect()

    async def controller_close(event):
        """Close connection when HASS shutsdown."""
        await controller.close()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, controller_close)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][MEDIA_PLAYER_DOMAIN] = controller.get_players()

    hass.async_create_task(async_load_platform(
        hass, MEDIA_PLAYER_DOMAIN, DOMAIN, {}, config))

    return True
