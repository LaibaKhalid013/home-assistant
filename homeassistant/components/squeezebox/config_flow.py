"""Config flow for Logitech Squeezebox integration."""
import asyncio
import logging

from pysqueezebox import Server, async_discover
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    HTTP_UNAUTHORIZED,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# pylint: disable=unused-import
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)

TIMEOUT = 5


class SqueezeboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Logitech Squeezebox."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize an instance of the squeezebox config flow."""
        self.data_schema = DATA_SCHEMA
        self.discovery_info = None

    async def _discover(self, uuid=None):
        """
        Discover an unconfigured LMS server.

        Parameters:
            uuid: search for this uuid (optional)
        """
        self.discovery_info = None
        discovery_event = asyncio.Event()

        def _discovery_callback(server):
            if server.uuid:
                if uuid:
                    # ignore non-matching uuid
                    if server.uuid != uuid:
                        return
                else:
                    # ignore already configured uuids
                    for entry in self._async_current_entries():
                        if entry.unique_id == server.uuid:
                            return
                self.discovery_info = {
                    CONF_HOST: server.host,
                    CONF_PORT: server.port,
                    "uuid": server.uuid,
                }
                _LOGGER.debug("Discovered server: %s", self.discovery_info)
                discovery_event.set()

        discovery_task = self.hass.async_create_task(
            async_discover(_discovery_callback)
        )

        await discovery_event.wait()
        discovery_task.cancel()  # stop searching as soon as we find server

        # update with suggested values from discovery
        self.data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    description={"suggested_value": self.discovery_info[CONF_HOST]},
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=DEFAULT_PORT,
                    description={"suggested_value": self.discovery_info[CONF_PORT]},
                ): int,
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
            }
        )

    async def _validate_input(self, data):
        """
        Validate the user input allows us to connect.

        Retrieve unique id and abort if already configured.

        Data has the keys from DATA_SCHEMA with values provided by the user.
        """
        server = Server(
            async_get_clientsession(self.hass),
            data[CONF_HOST],
            data[CONF_PORT],
            data.get(CONF_USERNAME),
            data.get(CONF_PASSWORD),
        )

        try:
            status = await server.async_query("serverstatus")
            if not status:
                if server.http_status == HTTP_UNAUTHORIZED:
                    return "invalid_auth"
                return "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            return "unknown"

        if "uuid" in status:
            await self.async_set_unique_id(status["uuid"])
            self._abort_if_unique_id_configured()

    async def async_step_user(self, user_input=None, errors=None):
        """Handle a flow initialized by the user."""
        if user_input and CONF_HOST in user_input:
            # update with host provided by user
            self.data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        description={"suggested_value": user_input.get(CONF_HOST)},
                    ): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT,): int,
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                }
            )
            return await self.async_step_edit()

        # no host specified, see if we can discover an unconfigured LMS server
        try:
            await asyncio.wait_for(self._discover(), timeout=TIMEOUT)
            return await self.async_step_edit()
        except asyncio.TimeoutError:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Optional(CONF_HOST): str}),
                errors={"base": "no_server_found"},
            )

        # display the form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_edit(self, user_input=None):
        """Edit a discovered or manually inputted server."""
        errors = {}
        if user_input:
            error = await self._validate_input(user_input)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="edit", data_schema=self.data_schema, errors=errors
        )

    async def async_step_import(self, config, errors=None):
        """Import a config flow from configuration."""
        DATA_SCHEMA(config)
        error = await self._validate_input(config)
        if error:
            return self.async_abort(reason=error)
        return self.async_create_entry(title=config[CONF_HOST], data=config)

    async def async_step_discovery(self, discovery_info):
        """Handle discovery."""
        _LOGGER.debug("Reached discovery flow with info: %s", discovery_info)
        DATA_SCHEMA(discovery_info)
        error = await self._validate_input(discovery_info)
        if error:
            return self.async_abort(reason=error)

        # update schema with suggested values from discovery
        self.data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    description={"suggested_value": discovery_info.get(CONF_HOST)},
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=DEFAULT_PORT,
                    description={"suggested_value": discovery_info.get(CONF_PORT)},
                ): int,
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
            }
        )
        return await self.async_step_edit()

    async def async_step_unignore(self, user_input):
        """Set up previously ignored Logitech Media Server."""
        unique_id = user_input["unique_id"]
        await self.async_set_unique_id(unique_id)
        # see if we can discover an unconfigured LMS server matching uuid
        try:
            await asyncio.wait_for(self._discover(unique_id), timeout=TIMEOUT)
            return await self.async_step_edit()
        except asyncio.TimeoutError:
            return self.async_abort(reason="no_server_found")


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
