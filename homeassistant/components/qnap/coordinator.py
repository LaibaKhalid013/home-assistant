"""Data coordinator for the qnap integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from qnapstats import QNAPStats

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

UPDATE_INTERVAL = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)


class QnapCoordinator(DataUpdateCoordinator[None]):
    """Custom coordinator for the qnap integration."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the qnap coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)

        protocol = "https" if config.data[CONF_SSL] else "http"
        self._api = QNAPStats(
            f"{protocol}://{config.data.get(CONF_HOST)}",
            config.data.get(CONF_PORT),
            config.data.get(CONF_USERNAME),
            config.data.get(CONF_PASSWORD),
            verify_ssl=config.data.get(CONF_VERIFY_SSL),
            timeout=config.data.get(CONF_TIMEOUT),
        )

    def _sync_update(self) -> dict[str, dict[str, Any]]:
        """Get the latest data from the Qnap API."""
        return {
            "system_stats": self._api.get_system_stats(),
            "system_health": self._api.get_system_health(),
            "smart_drive_health": self._api.get_smart_disk_health(),
            "volumes": self._api.get_volumes(),
            "bandwidth": self._api.get_bandwidth(),
        }

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Get the latest data from the Qnap API."""
        return await self.hass.async_add_executor_job(self._sync_update)
