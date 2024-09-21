"""Switcher integration Light platform."""

from __future__ import annotations

import logging
from typing import Any

from aioswitcher.api import SwitcherBaseResponse, SwitcherType2Api
from aioswitcher.device import DeviceCategory, DeviceState

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SIGNAL_DEVICE_ADD
from .coordinator import SwitcherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

API_SET_LIGHT = "set_light"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Switcher light from a config entry."""

    @callback
    def async_add_light(coordinator: SwitcherDataUpdateCoordinator) -> None:
        """Add light from Switcher device."""
        if (
            coordinator.data.device_type.category
            == DeviceCategory.SINGLE_SHUTTER_DUAL_LIGHT
        ):
            async_add_entities(
                [
                    SwitcherLightEntity(coordinator, 0),
                    SwitcherLightEntity(coordinator, 1),
                ]
            )

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DEVICE_ADD, async_add_light)
    )


class SwitcherLightEntity(
    CoordinatorEntity[SwitcherDataUpdateCoordinator], LightEntity
):
    """Representation of a Switcher light entity."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_has_entity_name = True
    _attr_name = None

    @property
    def name(self) -> str:
        """Name of the entity."""
        return "Light" + str(self._light_id + 1)

    def __init__(
        self,
        coordinator: SwitcherDataUpdateCoordinator,
        light_id: int | None = None,
    ):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._light_id = light_id
        self.control_result: bool | None = None

        # Entity class attributes
        self._attr_unique_id = (
            f"{coordinator.device_id}-{coordinator.mac_address}-{self._light_id}"
        )
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, coordinator.mac_address)}
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """When device updates, clear control result that overrides state."""
        self.control_result = None
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        if self.control_result is not None:
            return self.control_result

        if self._light_id == 0:
            return bool(self.coordinator.data.lights[0] == DeviceState.ON)
        return bool(self.coordinator.data.lights[1] == DeviceState.ON)

    async def _async_call_api(self, api: str, *args: Any) -> None:
        """Call Switcher API."""
        _LOGGER.debug("Calling api for %s, api: '%s', args: %s", self.name, api, args)
        response: SwitcherBaseResponse | None = None
        error = None

        try:
            async with SwitcherType2Api(
                self.coordinator.data.device_type,
                self.coordinator.data.ip_address,
                self.coordinator.data.device_id,
                self.coordinator.data.device_key,
                self.coordinator.token,
            ) as swapi:
                response = await getattr(swapi, api)(*args)
        except (TimeoutError, OSError, RuntimeError) as err:
            error = repr(err)

        if error or not response or not response.successful:
            self.coordinator.last_update_success = False
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Call api for {self.name} failed, api: '{api}', "
                f"args: {args}, response/error: {response or error}"
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._async_call_api(API_SET_LIGHT, DeviceState.ON, self._light_id)
        self.control_result = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._async_call_api(API_SET_LIGHT, DeviceState.OFF, self._light_id)
        self.control_result = False
        self.async_write_ha_state()
