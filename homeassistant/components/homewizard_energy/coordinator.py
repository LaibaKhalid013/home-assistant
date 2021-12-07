"""Update coordinator for HomeWizard Energy."""
import asyncio
import logging

import aiohwenergy
import async_timeout

from homeassistant.const import CONF_STATE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DATA, CONF_DEVICE, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HWEnergyDeviceUpdateCoordinator(DataUpdateCoordinator):
    """Gather data for the energy device."""

    host = None
    api = None

    def __init__(
        self,
        hass: HomeAssistant,
        host,
    ) -> None:
        """Initialize Update Coordinator."""

        self.host = host
        super().__init__(hass, _LOGGER, name="", update_interval=UPDATE_INTERVAL)

    async def _async_update_data(self) -> dict:
        """Fetch all device and sensor data from api."""

        async with async_timeout.timeout(10):

            if self.api is None:
                self.api = await self.initialize_api()

            # Update all properties
            status = await self.api.update()

            if not status:
                self.api = None
                raise UpdateFailed("Failed to communicate with device")

            data = {
                CONF_DEVICE: self.api.device,
                CONF_DATA: {},
                CONF_STATE: None,
            }

            for datapoint in self.api.data.available_datapoints:
                data[CONF_DATA][datapoint] = getattr(self.api.data, datapoint)

        return data

    async def initialize_api(self):
        """Initialize API and validate connection."""

        api = aiohwenergy.HomeWizardEnergy(self.host)

        try:
            await api.initialize()
            return api

        except (asyncio.TimeoutError, aiohwenergy.RequestError) as ex:
            raise UpdateFailed(
                f"Error connecting to the Energy device at {self.host}"
            ) from ex

        except aiohwenergy.DisabledError as ex:
            raise UpdateFailed("API disabled, API must be enabled in the app") from ex

        except aiohwenergy.AiohwenergyException as ex:
            raise UpdateFailed("Unknown Energy API error occurred") from ex

        except Exception as ex:  # pylint: disable=broad-except
            raise UpdateFailed(
                f"Unknown error connecting with Energy Device at {self.host}"
            ) from ex
