"""Select for Shelly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

from aioshelly.const import RPC_GENERATIONS

from homeassistant.components.select import (
    DOMAIN as SELECT_PLATFORM,
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ShellyConfigEntry, ShellyRpcCoordinator
from .entity import (
    RpcEntityDescription,
    ShellyRpcAttributeEntity,
    async_setup_entry_rpc,
)
from .utils import (
    async_remove_orphaned_virtual_entities,
    get_device_entry_gen,
    get_virtual_component_ids,
)


@dataclass(frozen=True, kw_only=True)
class RpcSelectDescription(RpcEntityDescription, SelectEntityDescription):
    """Class to describe a RPC select entity."""


RPC_SELECT_ENTITIES: Final = {
    "enum": RpcSelectDescription(
        key="enum",
        sub_key="value",
        has_entity_name=True,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ShellyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up selectors for device."""
    if get_device_entry_gen(config_entry) in RPC_GENERATIONS:
        coordinator = config_entry.runtime_data.rpc
        assert coordinator

        async_setup_entry_rpc(
            hass, config_entry, async_add_entities, RPC_SELECT_ENTITIES, RpcSelect
        )

        # the user can remove virtual components from the device configuration, so
        # we need to remove orphaned entities
        virtual_text_ids = get_virtual_component_ids(
            coordinator.device.config, SELECT_PLATFORM
        )
        async_remove_orphaned_virtual_entities(
            hass,
            config_entry.entry_id,
            coordinator.mac,
            SELECT_PLATFORM,
            "enum",
            virtual_text_ids,
        )


class RpcSelect(ShellyRpcAttributeEntity, SelectEntity):
    """Represent a RPC select entity."""

    entity_description: RpcSelectDescription

    def __init__(
        self,
        coordinator: ShellyRpcCoordinator,
        key: str,
        attribute: str,
        description: RpcSelectDescription,
    ) -> None:
        """Initialize select."""
        super().__init__(coordinator, key, attribute, description)

        titles = self.coordinator.device.config[key]["meta"]["ui"]["titles"]
        opts = self.coordinator.device.config[key]["options"]
        self.option_map = {
            opt: (titles[opt] if titles.get(opt) is not None else opt) for opt in opts
        }
        self.reversed_option_map = {tit: opt for opt, tit in self.option_map.items()}

        self._attr_options = list(self.option_map.values())

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return cast(str | None, self.option_map.get(self.attribute_value))

    async def async_select_option(self, option: str) -> None:
        """Change the value."""
        await self.call_rpc(
            "Enum.Set", {"id": self._id, "value": self.reversed_option_map[option]}
        )
