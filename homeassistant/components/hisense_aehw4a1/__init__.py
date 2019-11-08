"""The Hisense AEH-W4A1 integration."""
import ipaddress
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.climate import DOMAIN as CLIMA_DOMAIN
from homeassistant.const import CONF_IP_ADDRESS
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN


def coerce_ip(value):
    """Validate that provided value is a valid IP address."""
    if not value:
        raise vol.Invalid("Must define an IP address")
    try:
        ipaddress.IPv4Network(value)
    except ValueError:
        raise vol.Invalid("Not a valid IP address")
    return value


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            CLIMA_DOMAIN: vol.Schema(
                {
                    vol.Optional(CONF_IP_ADDRESS, default=[]): vol.Schema(
                        [vol.All(cv.string, coerce_ip)]
                    )
                }
            )
        }
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the Hisense AEH-W4A1 integration."""
    conf = config.get(DOMAIN)

    hass.data[DOMAIN] = conf or {}

    if conf is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}
            )
        )

    return True


async def async_setup_entry(hass, entry):
    """Set up a config entry for Hisense AEH-W4A1."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, CLIMA_DOMAIN)
    )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, CLIMA_DOMAIN)
