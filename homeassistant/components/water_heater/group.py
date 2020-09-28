"""Describe group states."""

from typing import Callable

from homeassistant.const import STATE_OFF
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType

from . import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_GAS,
    STATE_HEAT_PUMP,
    STATE_HIGH_DEMAND,
    STATE_PERFORMANCE,
)


@callback
def async_describe_on_off_states(
    hass: HomeAssistantType, async_on_off_states: Callable
) -> None:
    """Describe group on off states."""
    async_on_off_states(
        [
            STATE_ECO,
            STATE_ELECTRIC,
            STATE_PERFORMANCE,
            STATE_HIGH_DEMAND,
            STATE_HEAT_PUMP,
            STATE_GAS,
        ],
        STATE_OFF,
    )
