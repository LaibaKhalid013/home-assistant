"""Config flow to configure the iCloud integration."""
import logging
import os

import voluptuous as vol
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudException, PyiCloudFailedLoginException

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import slugify

# pylint: disable=unused-import
from .const import (
    CONF_ACCOUNT_NAME,
    CONF_GPS_ACCURACY_THRESHOLD,
    CONF_MAX_INTERVAL,
    DEFAULT_MAX_INTERVAL,
    DEFAULT_GPS_ACCURACY_THRESHOLD,
    DOMAIN,  # noqa
)

CONF_TRUSTED_DEVICE = "trusted_device"
CONF_VERIFICATION_CODE = "verification_code"

_LOGGER = logging.getLogger(__name__)


class IcloudFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a iCloud config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize iCloud config flow."""
        self.api = None
        self._username = None
        self._password = None
        self._account_name = None
        self._max_interval = None
        self._gps_accuracy_threshold = None

        self._trusted_device = None
        self._verification_code = None

    def _configuration_exists(self, username: str, account_name: str) -> bool:
        """Return True if username or account_name exists in configuration."""
        for entry in self._async_current_entries():
            if (
                entry.data[CONF_USERNAME] == username
                or entry.data.get(CONF_ACCOUNT_NAME) == account_name
                or slugify(entry.data[CONF_USERNAME].partition("@")[0]) == account_name
            ):
                return True
        return False

    async def _show_setup_form(self, user_input=None, errors=None):
        """Show the setup form to the user."""

        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                    ): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        icloud_dir = self.hass.config.path("icloud")
        if not os.path.exists(icloud_dir):
            await self.hass.async_add_executor_job(os.makedirs, icloud_dir)

        if user_input is None:
            return await self._show_setup_form(user_input, errors)

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._account_name = user_input.get(CONF_ACCOUNT_NAME)
        self._max_interval = user_input.get(CONF_MAX_INTERVAL, DEFAULT_MAX_INTERVAL)
        self._gps_accuracy_threshold = user_input.get(
            CONF_GPS_ACCURACY_THRESHOLD, DEFAULT_GPS_ACCURACY_THRESHOLD
        )

        if self._configuration_exists(self._username, self._account_name):
            errors[CONF_USERNAME] = "username_exists"
            return await self._show_setup_form(user_input, errors)

        try:
            self.api = await self.hass.async_add_executor_job(
                PyiCloudService, self._username, self._password, icloud_dir
            )
        except PyiCloudFailedLoginException as error:
            _LOGGER.error("Error logging into iCloud service: %s", error)
            self.api = None
            errors[CONF_USERNAME] = "login"
            return await self._show_setup_form(user_input, errors)

        _LOGGER.info("self.api.requires_2fa")
        _LOGGER.info(self.api.requires_2fa)
        if self.api.requires_2fa:
            try:
                if self._trusted_device is None:
                    return await self.async_step_trusted_device()

                if self._verification_code is None:
                    return await self.async_step_verification_code()

                self.api.authenticate()
                if self.api.requires_2fa:
                    errors["base"] = "unknown"
                    return await self._show_setup_form(user_input, errors)

                self._trusted_device = None
                self._verification_code = None

            except PyiCloudException as error:
                _LOGGER.error("Error setting up 2FA: %s", error)
                errors["base"] = "2fa"
                return await self._show_setup_form(user_input, errors)

        return self.async_create_entry(
            title=self._username,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_ACCOUNT_NAME: self._account_name,
                CONF_MAX_INTERVAL: self._max_interval,
                CONF_GPS_ACCURACY_THRESHOLD: self._gps_accuracy_threshold,
            },
        )

    async def async_step_import(self, user_input):
        """Import a config entry."""
        if self._configuration_exists(
            user_input[CONF_USERNAME], user_input.get(CONF_ACCOUNT_NAME)
        ):
            return self.async_abort(reason="username_exists")

        return await self.async_step_user(user_input)

    async def async_step_trusted_device(self, user_input=None, errors=None):
        """We need a trusted device."""
        if errors is None:
            errors = {}

        trusted_devices = {}
        devices = self.api.trusted_devices
        _LOGGER.info("self.api.trusted_devices")
        _LOGGER.info(devices)
        for i, device in enumerate(devices):
            trusted_devices[i] = device.get(
                "deviceName", f"SMS to {device.get('phoneNumber')}"
            )

        if user_input is None:
            return await self._show_trusted_device_form(
                trusted_devices, user_input, errors
            )

        self._trusted_device = self.api.trusted_devices[
            int(user_input[CONF_TRUSTED_DEVICE])
        ]

        _LOGGER.info("self._trusted_device")
        _LOGGER.info(self._trusted_device)
        _LOGGER.info("self.api.send_verification_code(self._trusted_device)")
        _LOGGER.info(self.api.send_verification_code(self._trusted_device))
        if not self.api.send_verification_code(self._trusted_device):
            _LOGGER.error("Failed to send verification code")
            self._trusted_device = None
            errors[CONF_TRUSTED_DEVICE] = "send_verification_code"

            return await self._show_trusted_device_form(
                trusted_devices, user_input, errors
            )

        # Trigger the next step immediately
        return await self.async_step_verification_code()

    async def _show_trusted_device_form(
        self, trusted_devices, user_input=None, errors=None
    ):
        """Show the trusted_device form to the user."""

        return self.async_show_form(
            step_id=CONF_TRUSTED_DEVICE,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TRUSTED_DEVICE): vol.All(
                        vol.Coerce(int), vol.In(trusted_devices)
                    )
                }
            ),
            errors=errors or {},
        )

    async def async_step_verification_code(self, user_input=None):
        """Ask the verification code to the user."""
        errors = {}

        if user_input is None:
            return await self._show_verification_code_form(user_input)

        self._verification_code = user_input[CONF_VERIFICATION_CODE]

        try:
            if not self.api.validate_verification_code(
                self._trusted_device, self._verification_code
            ):
                raise PyiCloudException("The code you entered is not valid.")
        except PyiCloudException as error:
            # Reset to the initial 2FA state to allow the user to retry
            _LOGGER.error("Failed to verify verification code: %s", error)
            self._trusted_device = None
            self._verification_code = None
            errors["base"] = "validate_verification_code"

            # Trigger the next step immediately
            return await self.async_step_trusted_device(None, errors)

        return await self.async_step_user(
            {
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_ACCOUNT_NAME: self._account_name,
                CONF_MAX_INTERVAL: self._max_interval,
                CONF_GPS_ACCURACY_THRESHOLD: self._gps_accuracy_threshold,
            }
        )

    async def _show_verification_code_form(self, user_input=None):
        """Show the verification_code form to the user."""

        return self.async_show_form(
            step_id=CONF_VERIFICATION_CODE,
            data_schema=vol.Schema({vol.Required(CONF_VERIFICATION_CODE): str}),
            errors=None,
        )
