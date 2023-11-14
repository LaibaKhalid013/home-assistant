"""Support for Valve devices."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from enum import IntFlag, StrEnum
import functools as ft
import logging
from typing import Any, ParamSpec, TypeVar, final

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_SET_VALVE_POSITION,
    SERVICE_STOP_VALVE,
    SERVICE_TOGGLE,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "valve"
SCAN_INTERVAL = timedelta(seconds=15)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

_P = ParamSpec("_P")
_R = TypeVar("_R")


class ValveDeviceClass(StrEnum):
    """Device class for valve."""

    # Refer to the valve dev docs for device class descriptions
    WATER = "water"
    GAS = "gas"


DEVICE_CLASSES_SCHEMA = vol.All(vol.Lower, vol.Coerce(ValveDeviceClass))


# mypy: disallow-any-generics
class ValveEntityFeature(IntFlag):
    """Supported features of the valve entity."""

    OPEN = 1
    CLOSE = 2
    SET_POSITION = 4
    STOP = 8


ATTR_CURRENT_POSITION = "current_position"
ATTR_POSITION = "position"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Track states and offer events for valves."""
    component = hass.data[DOMAIN] = EntityComponent[ValveEntity](
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )

    await component.async_setup(config)

    component.async_register_entity_service(
        SERVICE_OPEN_VALVE, {}, "async_open_valve", [ValveEntityFeature.OPEN]
    )

    component.async_register_entity_service(
        SERVICE_CLOSE_VALVE, {}, "async_close_valve", [ValveEntityFeature.CLOSE]
    )

    component.async_register_entity_service(
        SERVICE_SET_VALVE_POSITION,
        {
            vol.Required(ATTR_POSITION): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            )
        },
        "async_set_valve_position",
        [ValveEntityFeature.SET_POSITION],
    )

    component.async_register_entity_service(
        SERVICE_STOP_VALVE, {}, "async_stop_valve", [ValveEntityFeature.STOP]
    )

    component.async_register_entity_service(
        SERVICE_TOGGLE,
        {},
        "async_toggle",
        [ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE],
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: EntityComponent[ValveEntity] = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: EntityComponent[ValveEntity] = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


@dataclass
class ValveEntityDescription(EntityDescription):
    """A class that describes valve entities."""

    device_class: ValveDeviceClass | None = None


class ValveEntity(Entity):
    """Base class for valve entities."""

    entity_description: ValveEntityDescription
    _attr_current_valve_position: int | None = None
    _attr_device_class: ValveDeviceClass | None
    _attr_is_closed: bool | None
    _attr_is_closing: bool | None = None
    _attr_is_opening: bool | None = None
    _attr_supported_features: ValveEntityFeature = ValveEntityFeature(0)

    _valve_is_last_toggle_direction_open = True

    @property
    def current_valve_position(self) -> int | None:
        """Return current position of valve.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._attr_current_valve_position

    @property
    def device_class(self) -> ValveDeviceClass | None:
        """Return the class of this entity."""
        if hasattr(self, "_attr_device_class"):
            return self._attr_device_class
        if hasattr(self, "entity_description"):
            return self.entity_description.device_class
        return None

    @property
    @final
    def state(self) -> str | None:
        """Return the state of the valve."""
        if self.is_opening:
            self._valve_is_last_toggle_direction_open = True
            return STATE_OPENING
        if self.is_closing:
            self._valve_is_last_toggle_direction_open = False
            return STATE_CLOSING

        if (closed := self.is_closed) is None:
            return None

        return STATE_CLOSED if closed else STATE_OPEN

    @final
    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""

        return {ATTR_CURRENT_POSITION: self.current_valve_position}

    @property
    def supported_features(self) -> ValveEntityFeature:
        """Flag supported features."""
        return self._attr_supported_features

    @property
    def is_opening(self) -> bool | None:
        """Return if the valve is opening or not."""
        return self._attr_is_opening

    @property
    def is_closing(self) -> bool | None:
        """Return if the valve is closing or not."""
        return self._attr_is_closing

    @property
    def is_closed(self) -> bool | None:
        """Return if the valve is closed or not."""
        if hasattr(self, "_attr_is_closed"):
            return bool(self._attr_is_closed)
        if self.current_valve_position is None:
            return None
        return self.current_valve_position == 0

    def open_valve(self) -> None:
        """Open the valve."""
        raise NotImplementedError()

    async def async_open_valve(self) -> None:
        """Open the valve."""
        await self.hass.async_add_executor_job(ft.partial(self.open_valve))

    def close_valve(self) -> None:
        """Close valve."""
        raise NotImplementedError()

    async def async_close_valve(self) -> None:
        """Close valve."""
        await self.hass.async_add_executor_job(ft.partial(self.close_valve))

    def toggle(self) -> None:
        """Toggle the entity."""
        fns = {
            "open": self.open_valve,
            "close": self.close_valve,
            "stop": self.stop_valve,
        }
        function = self._get_toggle_function(fns)
        function()

    async def async_toggle(self) -> None:
        """Toggle the entity."""
        fns = {
            "open": self.async_open_valve,
            "close": self.async_close_valve,
            "stop": self.async_stop_valve,
        }
        function = self._get_toggle_function(fns)
        await function()

    def set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""

    async def async_set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""
        await self.hass.async_add_executor_job(
            ft.partial(self.set_valve_position, position)
        )

    def stop_valve(self) -> None:
        """Stop the valve."""

    async def async_stop_valve(self) -> None:
        """Stop the valve."""
        await self.hass.async_add_executor_job(ft.partial(self.stop_valve))

    def _get_toggle_function(
        self, fns: dict[str, Callable[_P, _R]]
    ) -> Callable[_P, _R]:
        if ValveEntityFeature.STOP | self.supported_features and (
            self.is_closing or self.is_opening
        ):
            return fns["stop"]
        if self.is_closed:
            return fns["open"]
        if self._valve_is_last_toggle_direction_open:
            return fns["close"]
        return fns["open"]
