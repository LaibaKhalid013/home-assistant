"""Provides time enties for Home Connect."""

from datetime import time
import logging

from homeconnect.api import HomeConnectError

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HomeConnectDevice
from .const import ATTR_VALUE, DOMAIN
from .entity import HomeConnectEntity

_LOGGER = logging.getLogger(__name__)


TIME_ENTITIES = (
    TimeEntityDescription(
        key="BSH.Common.Setting.AlarmClock",
        translation_key="alarm_clock",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Home Connect switch."""

    def get_entities():
        """Get a list of entities."""
        hc_api = hass.data[DOMAIN][config_entry.entry_id]
        return [
            HomeConnectTimeEntity(device, setting)
            for setting in TIME_ENTITIES
            for device_dict in hc_api.devices
            if setting.key in (device := device_dict[CONF_DEVICE]).appliance.status
        ]

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class HomeConnectTimeEntity(HomeConnectEntity, TimeEntity):
    """Time setting class for Home Connect."""

    entity_description: TimeEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        device: HomeConnectDevice,
        entity_description: TimeEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(device, entity_description.key, "")
        self.entity_description = entity_description
        del self._attr_name

    async def async_set_value(self, value: time) -> None:
        """Set the native value of the entity."""
        _LOGGER.debug(
            "Tried to set value %s to %s for %s",
            value,
            self.bsh_key,
            self.entity_id,
        )
        try:
            await self.hass.async_add_executor_job(
                self.device.appliance.set_setting,
                self.bsh_key,
                (value.hour * 60 + value.minute) * 60 + value.second,
            )
        except HomeConnectError as err:
            _LOGGER.error(
                "Error setting value %s to %s for %s: %s",
                value,
                self.bsh_key,
                self.entity_id,
                err,
            )

    async def async_update(self) -> None:
        """Update the Time setting status."""
        data = self.device.appliance.status.get(self.bsh_key)
        if data is None:
            _LOGGER.error("No value for %s", self.bsh_key)
            self._attr_native_value = None
            return
        seconds = data.get(ATTR_VALUE, None)
        self._attr_native_value = (
            time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
            if seconds is not None
            else None
        )
        _LOGGER.debug("Updated, new value: %s", self._attr_native_value)
