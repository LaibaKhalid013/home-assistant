"""Code to handle a Livisi switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LIVISI_REACHABILITY_CHANGE,
    LIVISI_STATE_CHANGE,
    LOGGER,
    PSS_DEVICE_TYPE,
)
from .coordinator import LivisiDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch device."""
    coordinator: LivisiDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def handle_coordinator_update() -> None:
        """Add switch."""
        shc_devices: list[dict[str, Any]] = coordinator.data
        for device in shc_devices:
            if device["type"] == PSS_DEVICE_TYPE:
                if device not in coordinator.switch_devices:
                    livisi_switch: SwitchEntity = create_entity(
                        config_entry, device, coordinator
                    )
                    LOGGER.debug("Include device type: %s", device.get("type"))
                    coordinator.switch_devices.append(device)
                    async_add_entities([livisi_switch])

    coordinator.async_add_listener(handle_coordinator_update)


def create_entity(
    config_entry: ConfigEntry,
    device: dict[str, Any],
    coordinator: LivisiDataUpdateCoordinator,
) -> SwitchEntity:
    """Create Switch Entity."""
    config_details: dict[str, Any] = device["config"]
    capabilities: list = device["capabilities"]
    room_id: str = device["location"].removeprefix("/location/")
    room_name: str = coordinator.rooms[room_id]
    livisi_switch = LivisiSwitch(
        config_entry,
        coordinator,
        unique_id=device["id"],
        manufacturer=device["manufacturer"],
        product=device["product"],
        serial_number=device["serialNumber"],
        device_type=device["type"],
        name=config_details["name"],
        capability_id=capabilities[0],
        room=room_name,
    )
    return livisi_switch


class LivisiSwitch(CoordinatorEntity[LivisiDataUpdateCoordinator], SwitchEntity):
    """Represents the Livisi Switch."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: LivisiDataUpdateCoordinator,
        unique_id,
        manufacturer,
        product,
        serial_number,
        device_type,
        name,
        capability_id,
        room,
        version=None,
    ):
        """Initialize the Livisi Switch."""
        self.config_entry = config_entry
        self._attr_unique_id = unique_id
        self._manufacturer = manufacturer
        self._product = product
        self._serial_number = serial_number
        self._attr_model = device_type
        self._attr_name = name
        self._state = None
        self._capability_id = capability_id
        self._room = room
        self._version = version
        self.aio_livisi = coordinator.aiolivisi
        self._attr_is_available = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._attr_unique_id))},
            manufacturer=self._manufacturer,
            model=self._attr_model,
            name=self._attr_name,
            suggested_area=self._room,
            sw_version=self._version,
        )
        super().__init__(coordinator)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        response = await self.aio_livisi.async_pss_set_state(
            self._capability_id, is_on=True
        )
        if response is None:
            self._attr_is_available = False
            raise HomeAssistantError(f"Failed to turn on {self._attr_name}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        response = await self.aio_livisi.async_pss_set_state(
            self._capability_id, is_on=False
        )
        if response is None:
            self._attr_is_available = False
            raise HomeAssistantError(f"Failed to turn off {self._attr_name}")

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._attr_is_on = await self.coordinator.async_get_pss_state(
            self._capability_id
        )
        async_dispatcher_connect(self.hass, LIVISI_STATE_CHANGE, self.update_states)
        async_dispatcher_connect(
            self.hass, LIVISI_REACHABILITY_CHANGE, self.update_reachability
        )

    @callback
    def update_states(self, device_id_state) -> None:
        """Update the states of the switch device."""
        if device_id_state is None:
            return
        if device_id_state.get("id") != self._capability_id:
            return
        on_state = device_id_state["state"]
        if on_state is None:
            return
        if on_state is True:
            self._attr_is_on = True
        else:
            self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def update_reachability(self, device_id_reachability) -> None:
        """Update the reachability of the switch device."""
        if device_id_reachability is None:
            return
        if device_id_reachability.get("id") != self.unique_id:
            return
        if device_id_reachability["is_reachable"] is False:
            self._attr_is_available = False
        else:
            self._attr_is_available = True
