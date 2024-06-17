"""Config flow for Sensoterra integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from sensoterra.customerapi import (
    CustomerApi,
    InvalidAuth as StInvalidAuth,
    Timeout as StTimeout,
)
import voluptuous as vol

from homeassistant.config_entries import SOURCE_USER, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN, TOKEN_EXPIRATION_DAYS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="email")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class SensoterraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensoterra."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create hub entry based on config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = CustomerApi(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            # We need a unique tag per HA instance
            uuid = self.hass.data["core.uuid"]
            expiration = datetime.now() + timedelta(TOKEN_EXPIRATION_DAYS)

            try:
                token: str = await api.get_token(
                    f"Home Assistant {uuid}", "READONLY", expiration
                )
            except StInvalidAuth as exp:
                _LOGGER.error(
                    "Login attempt with %s: %s", user_input[CONF_EMAIL], exp.message
                )
                errors["base"] = "invalid_auth"
            except StTimeout:
                _LOGGER.error("Login attempt with %s: time out", user_input[CONF_EMAIL])
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data={
                        CONF_TOKEN: token,
                        CONF_EMAIL: user_input[CONF_EMAIL],
                    },
                )

        return self.async_show_form(
            step_id=SOURCE_USER,
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )
