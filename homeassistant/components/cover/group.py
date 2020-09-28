"""Describe group states."""
from typing import Callable

from homeassistant.const import STATE_CLOSED, STATE_OPEN
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType


@callback
def async_describe_on_off_states(
    hass: HomeAssistantType, async_on_off_states: Callable
) -> None:
    """Describe group on off states."""
    async_on_off_states([STATE_OPEN], STATE_CLOSED)
