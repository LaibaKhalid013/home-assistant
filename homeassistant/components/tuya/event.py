"""Support for Tuya event entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_ENTITY_ID, CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TuyaConfigEntry
from .base import EnumTypeData, TuyaEntity
from .const import TUYA_DISCOVERY_NEW, TUYA_HA_EVENT, DPCode, DPType

# All descriptions can be found here. Mostly the Enum data types in the
# default status set of each category (that don't have a set instruction)
# end up being events.
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
EVENTS: dict[str, tuple[EventEntityDescription, ...]] = {
    # Wireless Switch
    # https://developer.tuya.com/en/docs/iot/s?id=Kbeoa9fkv6brp
    "wxkg": (
        EventEntityDescription(
            key=DPCode.SWITCH_MODE1,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "1"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE2,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "2"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE3,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "3"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE4,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "4"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE5,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "5"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE6,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "6"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE7,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "7"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE8,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "8"},
        ),
        EventEntityDescription(
            key=DPCode.SWITCH_MODE9,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "9"},
        ),
    )
}


async def async_setup_entry(
    hass: HomeAssistant, entry: TuyaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tuya events dynamically through Tuya discovery."""
    hass_data = entry.runtime_data

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Tuya binary sensor."""
        entities: list[TuyaEventEntity] = []
        for device_id in device_ids:
            device = hass_data.manager.device_map[device_id]
            if descriptions := EVENTS.get(device.category):
                for description in descriptions:
                    dpcode = description.key
                    if dpcode in device.status:
                        entities.append(
                            TuyaEventEntity(device, hass_data.manager, description)
                        )

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaEventEntity(TuyaEntity, EventEntity):
    """Tuya Event Entity."""

    entity_description: EventEntityDescription

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: EventEntityDescription,
    ) -> None:
        """Init Tuya event entity."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}.{description.key}"

        status_range = getattr(device, "status_range")

        if (
            description.key in status_range
            and status_range[description.key].type == DPType.ENUM
            and (
                enum_type := EnumTypeData.from_json(
                    DPCode(description.key), status_range[description.key].values
                )
            )
        ):
            self._attr_event_types: list[str] = enum_type.range

    @callback
    async def _handle_state_update(
        self, updated_status_properties: list[str] | None
    ) -> None:
        if (
            updated_status_properties is None
            or self.entity_description.key not in updated_status_properties
        ):
            return

        value = self.device.status.get(self.entity_description.key)
        self._trigger_event(value)
        self.async_write_ha_state()
        if TYPE_CHECKING:
            assert self.device_entry
            assert self.registry_entry
        event_data = {
            CONF_DEVICE_ID: self.device_entry.id,
            CONF_ENTITY_ID: self.registry_entry.id,
            CONF_TYPE: value,
        }
        self.hass.bus.async_fire(TUYA_HA_EVENT, event_data)
