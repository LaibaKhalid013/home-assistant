"""Adds config flow for GIOS."""
import asyncio

from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
from gios import ApiError, Gios, NoStationError
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_STATION_ID, DEFAULT_NAME, DOMAIN  # pylint:disable=unused-import

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION_ID): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class GiosFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GIOS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                already_configured = self._async_current_ids()
                if user_input[CONF_STATION_ID] in already_configured:
                    raise StationIdExists()

                websession = async_get_clientsession(self.hass)

                with timeout(30):
                    gios = Gios(user_input[CONF_STATION_ID], websession)
                    await gios.update()

                if not gios.available:
                    raise InvalidSensorsData()

                await self.async_set_unique_id(
                    user_input[CONF_STATION_ID], raise_on_progress=False
                )
                return self.async_create_entry(
                    title=user_input[CONF_STATION_ID], data=user_input,
                )
            except StationIdExists:
                errors[CONF_STATION_ID] = "station_id_exists"
            except (ApiError, ClientConnectorError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except NoStationError:
                errors[CONF_STATION_ID] = "wrong_station_id"
            except InvalidSensorsData:
                errors[CONF_STATION_ID] = "invalid_sensors_data"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class InvalidSensorsData(exceptions.HomeAssistantError):
    """Error to indicate invalid sensors data."""


class StationIdExists(exceptions.HomeAssistantError):
    """Error to indicate that station with station_id is already configured."""
