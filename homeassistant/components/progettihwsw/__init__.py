"""Automation manager for boards manufactured by ProgettiHWSW Italy."""

from ProgettiHWSW.ProgettiHWSWAPI import ProgettiHWSWAPI
from ProgettiHWSW.analog import AnalogInput
from ProgettiHWSW.input import Input
from ProgettiHWSW.relay import Relay
from ProgettiHWSW.temperature import Temperature

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["switch", "binary_sensor", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ProgettiHWSW Automation from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = ProgettiHWSWAPI(
        f'{entry.data["host"]}:{entry.data["port"]}'
    )

    # Check board validation again to load new values to API.
    await hass.data[DOMAIN][entry.entry_id].check_board()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def setup_input(api: ProgettiHWSWAPI, input_number: int) -> Input:
    """Initialize the input pin."""
    return api.get_input(input_number)


def setup_switch(api: ProgettiHWSWAPI, switch_number: int, mode: str) -> Relay:
    """Initialize the output pin."""
    return api.get_relay(switch_number, mode)


def setup_temperature(api: ProgettiHWSWAPI, input_number: int) -> Temperature:
    """Initialize the output pin."""
    return api.get_temp(input_number)


def setup_analog(api: ProgettiHWSWAPI, input_number: int) -> AnalogInput:
    """Initialize the output pin."""
    return api.get_pot(input_number)
