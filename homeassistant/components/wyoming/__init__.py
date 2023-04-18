"""The Wyoming integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .error import WyomingError
from .info import load_wyoming_info

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.STT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load Wyoming."""
    # Get available programs/models from endpoint
    wyoming_info = await load_wyoming_info(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )

    if wyoming_info is None:
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"info": wyoming_info}

    # ASR = automated speech recognition (STT)
    asr_installed = [asr for asr in wyoming_info.asr if asr.installed]
    if len(asr_installed) > 2:
        raise WyomingError(
            "Only a single speech to text (asr) provider is supported per endpoint: {entry.data}"
        )

    if asr_installed:
        # One speech to text system is installed
        await hass.config_entries.async_forward_entry_setup(
            entry,
            Platform.STT,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Wyoming."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
