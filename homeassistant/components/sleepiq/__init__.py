"""Support for SleepIQ from SleepNumber."""
import logging

from sleepyq import Sleepyq
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DATA_SLEEPIQ, DOMAIN
from .coordinator import SleepIQDataUpdateCoordinator
from .models import SleepIQHassData

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
    },
    extra=vol.ALLOW_EXTRA,
)


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up sleepiq component."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the SleepIQ config entry."""
    client = Sleepyq(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        await hass.async_add_executor_job(client.login)
    except ValueError:
        _LOGGER.error("SleepIQ login failed, double check your username and password")
        return False

    coordinator = SleepIQDataUpdateCoordinator(
        hass,
        client=client,
        username=entry.data[CONF_USERNAME],
    )

    # Call the SleepIQ API to refresh data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DATA_SLEEPIQ] = SleepIQHassData(
        coordinators={entry.data[CONF_USERNAME]: coordinator}
    )

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload the config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    hass.data[DATA_SLEEPIQ].coordinators.pop(config_entry.data[CONF_USERNAME])

    return unload_ok
