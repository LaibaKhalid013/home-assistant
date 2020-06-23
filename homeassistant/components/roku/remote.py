"""Support for the Roku remote."""
from typing import Callable, List

import voluptuous as vol

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
from homeassistant.helpers.typing import HomeAssistantType

from . import RokuDataUpdateCoordinator, RokuEntity, roku_exception_handler
from .const import ATTR_KEYWORD, DOMAIN, SERVICE_SEARCH


SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_KEYWORD): str,
    }
)


async def async_setup_entry(
    hass: HomeAssistantType,
    entry: ConfigEntry,
    async_add_entities: Callable[[List, bool], None],
) -> bool:
    """Load Roku remote based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unique_id = coordinator.data.info.serial_number
    async_add_entities([RokuRemote(unique_id, coordinator)], True)

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_SEARCH, SEARCH_SCHEMA, "search",
    )


class RokuRemote(RokuEntity, RemoteEntity):
    """Device that sends commands to an Roku."""

    def __init__(self, unique_id: str, coordinator: RokuDataUpdateCoordinator) -> None:
        """Initialize the Roku device."""
        super().__init__(
            device_id=unique_id,
            name=coordinator.data.info.name,
            coordinator=coordinator,
        )

        self._unique_id = unique_id

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return self._unique_id

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return not self.coordinator.data.state.standby

    @roku_exception_handler
    async def search(self, keyword):
        """Emulate opening search screen and entering keyword."""
        await self.coordinator.roku.search(keyword)

    @roku_exception_handler
    async def async_turn_on(self, **kwargs) -> None:
        """Turn the device on."""
        await self.coordinator.roku.remote("poweron")

    @roku_exception_handler
    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self.coordinator.roku.remote("poweroff")

    @roku_exception_handler
    async def async_send_command(self, command: List, **kwargs) -> None:
        """Send a command to one device."""
        num_repeats = kwargs[ATTR_NUM_REPEATS]

        for _ in range(num_repeats):
            for single_command in command:
                await self.coordinator.roku.remote(single_command)
