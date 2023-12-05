"""Tessie Data Coordinator."""
from datetime import timedelta
from http import HTTPStatus
import logging
from typing import Any

from aiohttp import ClientResponseError, ClientSession
from tessie_api import get_state

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

TESSIE_SYNC_INTERVAL = 15

_LOGGER = logging.getLogger(__name__)


class TessieDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Tessie API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        vin: str,
        data: dict[str, Any],
    ) -> None:
        """Initialize Tessie Data Update Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tessie",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=TESSIE_SYNC_INTERVAL),
        )
        self.api_key: str = api_key
        self.vin: str = vin
        self.session: ClientSession = async_get_clientsession(hass)
        self.data = data

    async def async_update_data(self) -> dict[str, Any]:
        """Update vehicle data using Tessie API."""
        try:
            vehicle = await get_state(
                session=self.session,
                api_key=self.api_key,
                vin=self.vin,
                use_cache=False,
            )
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

        if vehicle["state"] == "online":
            return vehicle

        # Use existing data but update state
        self.data["state"] = vehicle["state"]
        return self.data
