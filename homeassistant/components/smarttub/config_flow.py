"""Config flow to configure the SmartTub integration."""
import logging

from smarttub import LoginFailed
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import CONF_CONFIG_ENTRY, DOMAIN
from .controller import SmartTubController

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


_LOGGER = logging.getLogger(__name__)


class SmartTubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SmartTub configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Instantiate config flow."""
        super().__init__()
        self._reauth_input = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        controller = SmartTubController(self.hass)
        try:
            account = await controller.login(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
        except LoginFailed:
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        import pdb

        pdb.set_trace()
        existing_entry = await self.async_set_unique_id(account.id)
        if self._reauth_input is not None:
            # this is a reauth attempt
            if existing_entry:
                if (
                    existing_entry.unique_id
                    != self._reauth_input[CONF_CONFIG_ENTRY].unique_id
                ):
                    # there is a config entry matching this account, but it is not the one we were trying to reauth
                    return self.async_abort(reason="already_configured")
                self.hass.config_entries.async_update_entry(
                    existing_entry, data=user_input
                )
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title=user_input[CONF_EMAIL], data=user_input)

    async def async_step_reauth(self, user_input=None):
        """Get new credentials if the current ones don't work anymore."""
        if user_input is not None:
            self._reauth_input = dict(user_input)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"email": self._reauth_input[CONF_EMAIL]},
                data_schema=DATA_SCHEMA,
            )
        return await self.async_step_user()
