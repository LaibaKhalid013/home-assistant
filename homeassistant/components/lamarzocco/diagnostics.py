"""Diagnostics support for La Marzocco."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LaMarzoccoUpdateCoordinator

TO_REDACT = {
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: LaMarzoccoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device = coordinator.device
    # collect all data sources
    data = {}
    data["model"] = device.model
    data["config"] = asdict(device.config)
    data["firmware"] = [
        {key: asdict(firmware)} for key, firmware in device.firmware.items()
    ]
    data["statistics"] = asdict(device.statistics)

    return async_redact_data(data, TO_REDACT)
