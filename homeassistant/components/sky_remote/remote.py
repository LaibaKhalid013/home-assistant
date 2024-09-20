"""Home Assistant integration to control a sky box using the remote platform."""

from collections.abc import Iterable
import logging
from typing import Any

from skyboxremote import VALID_KEYS

from homeassistant.components.remote import RemoteEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RemoteControl, SkyRemoteConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: SkyRemoteConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sky remote platform."""
    async_add_entities(
        [
            SkyRemote(
                config.runtime_data.remote, config.data[CONF_HOST], config.entry_id
            )
        ],
        True,
    )


class SkyRemote(RemoteEntity):
    """Representation of a Sky Remote."""

    def __init__(self, remote: RemoteControl, name: str, unique_id: str) -> None:
        """Initialize the Sky Remote."""
        self._remote = remote
        self._is_on = True
        self._attr_unique_id = unique_id
        self._attr_name = name

    def turn_on(self, activity: str | None = None, **kwargs: Any) -> None:
        """Send the power on command."""
        self.send_command(["sky"])

    def turn_off(self, activity: str | None = None, **kwargs: Any) -> None:
        """Send the power command."""
        self.send_command(["power"])

    def send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a list of commands to the device."""
        for cmd in command:
            if cmd not in VALID_KEYS:
                raise ServiceValidationError(
                    f"{cmd} is not in Valid Keys: {VALID_KEYS}"
                )
        try:
            self._remote.send_keys(command)
        except ValueError as err:
            _LOGGER.error("Invalid command: %s. Error: %s", command, err)
            return
        _LOGGER.debug("Successfully sent command %s", command)
