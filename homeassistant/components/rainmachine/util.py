"""Define RainMachine utilities."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any


from homeassistant.backports.enum import StrEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import LOGGER

SIGNAL_REBOOT_REQUESTED = "rainmachine_reboot_requested_{0}"


class RunStates(StrEnum):
    """Define an enum for program/zone run states."""

    NOT_RUNNING = "Not Running"
    QUEUED = "Queued"
    RUNNING = "Running"


RUN_STATE_MAP = {
    0: RunStates.NOT_RUNNING,
    1: RunStates.RUNNING,
    2: RunStates.QUEUED,
}


def key_exists(data: dict[str, Any], search_key: str) -> bool:
    """Return whether a key exists in a nested dict."""
    for key, value in data.items():
        if key == search_key:
            return True
        if isinstance(value, dict):
            return key_exists(value, search_key)
    return False


class RainMachineDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Define an extended DataUpdateCoordinator."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
        name: str,
        update_interval: timedelta,
        update_method: Callable[..., Awaitable],
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name=name,
            update_interval=update_interval,
            update_method=update_method,
        )

        self._signal_handler_unsubs: list[Callable[..., None]] = []

        self.config_entry = entry
        self.signal_reboot_requested = SIGNAL_REBOOT_REQUESTED.format(
            self.config_entry.entry_id
        )

    async def async_initialize(self) -> None:
        """Initialize the coordinator."""

        @callback
        def async_reboot_requested() -> None:
            """Respond to a reboot request."""
            self.last_update_success = False
            self.async_update_listeners()

        self._signal_handler_unsubs.append(
            async_dispatcher_connect(
                self.hass, self.signal_reboot_requested, async_reboot_requested
            )
        )

        @callback
        def async_teardown() -> None:
            """Tear the coordinator down appropriately."""
            for unsub in self._signal_handler_unsubs:
                unsub()

        self.config_entry.async_on_unload(async_teardown)
