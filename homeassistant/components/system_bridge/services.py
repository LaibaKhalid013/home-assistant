"""System Bridge services."""

from dataclasses import asdict
import logging
from typing import Any

from systembridgemodels.keyboard_key import KeyboardKey
from systembridgemodels.keyboard_text import KeyboardText
from systembridgemodels.modules.processes import Process
from systembridgemodels.open_path import OpenPath
from systembridgemodels.open_url import OpenUrl
import voluptuous as vol

from homeassistant.const import CONF_COMMAND, CONF_ID, CONF_NAME, CONF_PATH, CONF_URL
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN
from .coordinator import SystemBridgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CONF_BRIDGE = "bridge"
CONF_KEY = "key"
CONF_TEXT = "text"

SERVICE_GET_PROCESS_BY_ID = "get_process_by_id"
SERVICE_GET_PROCESSES_BY_NAME = "get_processes_by_name"
SERVICE_OPEN_PATH = "open_path"
SERVICE_POWER_COMMAND = "power_command"
SERVICE_OPEN_URL = "open_url"
SERVICE_SEND_KEYPRESS = "send_keypress"
SERVICE_SEND_TEXT = "send_text"

POWER_COMMAND_MAP = {
    "hibernate": "power_hibernate",
    "lock": "power_lock",
    "logout": "power_logout",
    "restart": "power_restart",
    "shutdown": "power_shutdown",
    "sleep": "power_sleep",
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up System Bridge services."""

    def valid_device(device: str) -> str:
        """Check device is valid."""
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device)
        if device_entry is not None:
            try:
                return next(
                    entry.entry_id
                    for entry in hass.config_entries.async_entries(DOMAIN)
                    if entry.entry_id in device_entry.config_entries
                )
            except StopIteration as exception:
                raise vol.Invalid(f"Could not find device {device}") from exception
        raise vol.Invalid(f"Device {device} does not exist")

    async def handle_get_process_by_id(service_call: ServiceCall) -> ServiceResponse:
        """Handle the get process by id service call."""
        _LOGGER.debug("Get process by id: %s", service_call.data)
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        processes: list[Process] = coordinator.data.processes

        # Find process.id from list, raise ServiceValidationError if not found
        try:
            return asdict(
                next(
                    process
                    for process in processes
                    if process.id == service_call.data[CONF_ID]
                )
            )
        except StopIteration as exception:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="process_not_found",
                translation_placeholders={"id": service_call.data[CONF_ID]},
            ) from exception

    async def handle_get_processes_by_name(
        service_call: ServiceCall,
    ) -> ServiceResponse:
        """Handle the get process by name service call."""
        _LOGGER.debug("Get process by name: %s", service_call.data)
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        processes: list[Process] = coordinator.data.processes
        # Find processes from list
        items: list[dict[str, Any]] = [
            asdict(process)
            for process in processes
            if process.name is not None
            and service_call.data[CONF_NAME].lower() in process.name.lower()
        ]

        return {
            "count": len(items),
            "processes": list(items),
        }

    async def handle_open_path(service_call: ServiceCall) -> ServiceResponse:
        """Handle the open path service call."""
        _LOGGER.debug("Open path: %s", service_call.data)
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        response = await coordinator.websocket_client.open_path(
            OpenPath(path=service_call.data[CONF_PATH])
        )
        return asdict(response)

    async def handle_power_command(service_call: ServiceCall) -> ServiceResponse:
        """Handle the power command service call."""
        _LOGGER.debug("Power command: %s", service_call.data)
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        response = await getattr(
            coordinator.websocket_client,
            POWER_COMMAND_MAP[service_call.data[CONF_COMMAND]],
        )()
        return asdict(response)

    async def handle_open_url(service_call: ServiceCall) -> ServiceResponse:
        """Handle the open url service call."""
        _LOGGER.debug("Open URL: %s", service_call.data)
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        response = await coordinator.websocket_client.open_url(
            OpenUrl(url=service_call.data[CONF_URL])
        )
        return asdict(response)

    async def handle_send_keypress(service_call: ServiceCall) -> ServiceResponse:
        """Handle the send_keypress service call."""
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        response = await coordinator.websocket_client.keyboard_keypress(
            KeyboardKey(key=service_call.data[CONF_KEY])
        )
        return asdict(response)

    async def handle_send_text(service_call: ServiceCall) -> ServiceResponse:
        """Handle the send_keypress service call."""
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            service_call.data[CONF_BRIDGE]
        ]
        response = await coordinator.websocket_client.keyboard_text(
            KeyboardText(text=service_call.data[CONF_TEXT])
        )
        return asdict(response)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PROCESS_BY_ID,
        handle_get_process_by_id,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_ID): cv.positive_int,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PROCESSES_BY_NAME,
        handle_get_processes_by_name,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_NAME): cv.string,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_PATH,
        handle_open_path,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_PATH): cv.string,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_POWER_COMMAND,
        handle_power_command,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_COMMAND): vol.In(POWER_COMMAND_MAP),
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_URL,
        handle_open_url,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_URL): cv.string,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_KEYPRESS,
        handle_send_keypress,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_KEY): cv.string,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEXT,
        handle_send_text,
        schema=vol.Schema(
            {
                vol.Required(CONF_BRIDGE): valid_device,
                vol.Required(CONF_TEXT): cv.string,
            },
        ),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload System Bridge services."""
    hass.services.async_remove(DOMAIN, SERVICE_OPEN_PATH)
