"""Config flow for the Jellyfin integration."""
from __future__ import annotations

import logging
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .client_wrapper import CannotConnect, InvalidAuth, create_client, validate_input
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jellyfin."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a user defined configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = str(uuid.uuid4())
            client = create_client(client_id)
            try:
                userid = await validate_input(self.hass, user_input, client)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as ex:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                _LOGGER.exception(ex)
            else:
                await self.async_set_unique_id(userid)
                self._abort_if_unique_id_configured()

                data = user_input
                data[CONF_CLIENT_ID] = client_id

                return self.async_create_entry(title=user_input[CONF_URL], data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
