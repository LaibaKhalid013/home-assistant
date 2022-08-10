"""Config flow for Switchbot."""
from __future__ import annotations

import logging
from typing import Any

from switchbot import SwitchBotAdvertisement, parse_advertisement_data
import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_PASSWORD, CONF_SENSOR_TYPE
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult

from .const import CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT, DOMAIN, SUPPORTED_MODEL_TYPES

_LOGGER = logging.getLogger(__name__)


def format_unique_id(address: str) -> str:
    """Format the unique ID for a switchbot."""
    return address.replace(":", "").lower()


def short_address(address: str) -> str:
    """Convert a Bluetooth address to a short address."""
    results = address.replace("-", ":").split(":")
    return f"{results[-2].upper()}{results[-1].upper()}"[-4:]


def name_from_discovery(discovery: SwitchBotAdvertisement) -> str:
    """Get the name from a discovery."""
    return f'{discovery.data["modelFriendlyName"]} {short_address(discovery.address)}'


class SwitchbotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Switchbot."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SwitchbotOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SwitchbotOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_adv: SwitchBotAdvertisement | None = None
        self._discovered_advs: dict[str, SwitchBotAdvertisement] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered bluetooth device: %s", discovery_info)
        await self.async_set_unique_id(format_unique_id(discovery_info.address))
        self._abort_if_unique_id_configured()
        parsed = parse_advertisement_data(
            discovery_info.device, discovery_info.advertisement
        )
        if not parsed or parsed.data.get("modelName") not in SUPPORTED_MODEL_TYPES:
            return self.async_abort(reason="not_supported")
        self._discovered_adv = parsed
        data = parsed.data
        self.context["title_placeholders"] = {
            "name": data["modelFriendlyName"],
            "address": short_address(discovery_info.address),
        }
        if self._discovered_adv.data["isEncrypted"]:
            return await self.async_step_password()
        return await self.async_step_confirm()

    async def _async_create_entry_from_discovery(
        self, user_input: dict[str, Any]
    ) -> FlowResult:
        """Create an entry from a discovery."""
        assert self._discovered_adv is not None
        discovery = self._discovered_adv
        name = name_from_discovery(discovery)
        model_name = discovery.data["modelName"]
        return self.async_create_entry(
            title=name,
            data={
                **user_input,
                CONF_ADDRESS: discovery.address,
                CONF_SENSOR_TYPE: str(SUPPORTED_MODEL_TYPES[model_name]),
            },
        )

    async def async_step_confirm(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Confirm a single device."""
        assert self._discovered_adv is not None
        if user_input is not None:
            return await self._async_create_entry_from_discovery(user_input)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": name_from_discovery(self._discovered_adv)
            },
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the password step."""
        assert self._discovered_adv is not None
        if user_input is not None:
            # There is currently no api to validate the password
            # that does not operate the device so we have
            # to accept it as-is
            return await self._async_create_entry_from_discovery(user_input)

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={
                "name": name_from_discovery(self._discovered_adv)
            },
        )

    @callback
    def _async_discover_devices(self) -> None:
        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if (
                format_unique_id(address) in current_addresses
                or address in self._discovered_advs
            ):
                continue
            parsed = parse_advertisement_data(
                discovery_info.device, discovery_info.advertisement
            )
            if parsed and parsed.data.get("modelName") in SUPPORTED_MODEL_TYPES:
                self._discovered_advs[address] = parsed

        if not self._discovered_advs:
            raise AbortFlow("no_unconfigured_devices")

    async def _async_set_device(self, discovery: SwitchBotAdvertisement) -> None:
        """Set the device to work with."""
        self._discovered_adv = discovery
        address = discovery.address
        await self.async_set_unique_id(
            format_unique_id(address), raise_on_progress=False
        )
        self._abort_if_unique_id_configured()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}
        device_adv: SwitchBotAdvertisement | None = None
        if user_input is not None:
            device_adv = self._discovered_advs[user_input[CONF_ADDRESS]]
            await self._async_set_device(device_adv)
            if device_adv.data["isEncrypted"]:
                return await self.async_step_password()
            return await self._async_create_entry_from_discovery(user_input)

        self._async_discover_devices()
        if len(self._discovered_advs) == 1:
            # If there is only one device we can ask for a password
            # or simply confirm it
            device_adv = list(self._discovered_advs.values())[0]
            await self._async_set_device(device_adv)
            if device_adv.data["isEncrypted"]:
                return await self.async_step_password()
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: name_from_discovery(parsed)
                            for address, parsed in self._discovered_advs.items()
                        }
                    ),
                }
            ),
            errors=errors,
        )


class SwitchbotOptionsFlowHandler(OptionsFlow):
    """Handle Switchbot options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Switchbot options."""
        if user_input is not None:
            # Update common entity options for all other entities.
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_RETRY_COUNT,
                default=self.config_entry.options.get(
                    CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT
                ),
            ): int
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
