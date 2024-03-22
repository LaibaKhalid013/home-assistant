"""Button platform for La Marzocco espresso machines."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Generic

from lmcloud.lm_machine import LaMarzoccoMachine

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import LaMarzoccoEntity, LaMarzoccoEntityDescription, _DeviceT


@dataclass(frozen=True, kw_only=True)
class LaMarzoccoButtonEntityDescription(
    LaMarzoccoEntityDescription,
    ButtonEntityDescription,
    Generic[_DeviceT],
):
    """Description of a La Marzocco button."""

    press_fn: Callable[[_DeviceT], Coroutine[Any, Any, None]]


ENTITIES: tuple[LaMarzoccoButtonEntityDescription, ...] = (
    LaMarzoccoButtonEntityDescription[LaMarzoccoMachine](
        key="start_backflush",
        translation_key="start_backflush",
        press_fn=lambda machine: machine.start_backflush(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        LaMarzoccoButtonEntity(coordinator, description)
        for description in ENTITIES
        if description.supported_fn(coordinator)
    )


class LaMarzoccoButtonEntity(LaMarzoccoEntity, ButtonEntity):
    """La Marzocco Button Entity."""

    entity_description: LaMarzoccoButtonEntityDescription

    async def async_press(self) -> None:
        """Press button."""
        await self.entity_description.press_fn(self.coordinator.device)
