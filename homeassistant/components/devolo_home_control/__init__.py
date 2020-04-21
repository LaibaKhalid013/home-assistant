"""The devolo_home_control integration."""
from devolo_home_control_api.homecontrol import HomeControl
from devolo_home_control_api.mydevolo import (
    Mydevolo,
    WrongCredentialsError,
    WrongUrlError,
)

from homeassistant.components import switch as ha_switch
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import HomeAssistantType

from .config_flow import create_config_flow
from .const import DOMAIN, HOMECONTROL, MYDEVOLO, PLATFORMS

SUPPORTED_PLATFORMS = [ha_switch.DOMAIN]


async def async_setup(hass, config):
    """Get all devices and add them to hass."""
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up the devolo account from a config entry."""
    conf = entry.data
    hass.data.setdefault(DOMAIN, {})
    try:
        mydevolo = Mydevolo.get_instance()
    except SyntaxError:
        mydevolo = Mydevolo()
    try:
        mydevolo.user = conf.get(CONF_USERNAME)
        mydevolo.password = conf.get(CONF_PASSWORD)
        mydevolo.url = conf.get(MYDEVOLO)
        mydevolo.mprm = conf.get(HOMECONTROL)
    except (WrongCredentialsError, WrongUrlError):
        create_config_flow(hass=hass)
        raise ConfigEntryNotReady

    if mydevolo.maintenance():
        raise ConfigEntryNotReady

    gateway_id = mydevolo.get_gateway_ids()[0]
    mprm_url = mydevolo.mprm

    try:
        hass.data[DOMAIN]["homecontrol"] = HomeControl(
            gateway_id=gateway_id, url=mprm_url
        )
    except ConnectionError:
        raise ConfigEntryNotReady

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    def shutdown(event):
        hass.data[DOMAIN]["homecontrol"].websocket_disconnect(
            f"websocket disconnect requested by {EVENT_HOMEASSISTANT_STOP}"
        )

    # Listen when EVENT_HOMEASSISTANT_STOP is fired
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown)

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload = await hass.config_entries.async_forward_entry_unload(
        config_entry, "switch"
    )

    hass.data[DOMAIN]["homecontrol"].websocket_disconnect()
    del hass.data[DOMAIN]["homecontrol"]
    return unload
