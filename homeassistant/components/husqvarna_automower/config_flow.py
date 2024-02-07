"""Config flow to add the integration via the UI."""
from collections.abc import Mapping
import logging
from typing import Any

from aioautomower.utils import async_structure_token

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)
CONF_USER_ID = "user_id"


class HusqvarnaConfigFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a config flow."""

    VERSION = 1
    DOMAIN = DOMAIN
    reauth_entry: ConfigEntry | None = None

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an entry for the flow."""
        token = data[CONF_TOKEN]
        user_id = token[CONF_USER_ID]
        structured_token = await async_structure_token(token[CONF_ACCESS_TOKEN])
        first_name = structured_token.user.first_name
        last_name = structured_token.user.last_name
        await self.async_set_unique_id(user_id)
        if self.reauth_entry:
            self.hass.config_entries.async_update_entry(self.reauth_entry, data=data)
            await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"{NAME} of {first_name} {last_name}",
            data=data,
        )

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        _LOGGER.debug("self.reauth_entry :%s", self.reauth_entry)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauth dialog."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()
