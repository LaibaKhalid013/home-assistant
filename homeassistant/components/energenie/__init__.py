"""The Energenie integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energenie from a config entry."""

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True
