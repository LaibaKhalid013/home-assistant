"""Support for KNX/IP time."""

from __future__ import annotations

from datetime import time as dt_time
import time as time_time
from typing import Final

from xknx import XKNX
from xknx.devices import DateTime as XknxDateTime

from homeassistant import config_entries
from homeassistant.components.time import TimeEntity
from homeassistant.const import (
    CONF_ENTITY_CATEGORY,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_RESPOND_TO_READ,
    CONF_STATE_ADDRESS,
    CONF_SYNC_STATE,
    DATA_KNX_CONFIG,
    DOMAIN,
    KNX_ADDRESS,
)
from .knx_entity import KnxEntity

_TIME_TRANSLATION_FORMAT: Final = "%H:%M:%S"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities for KNX platform."""
    xknx: XKNX = hass.data[DOMAIN].xknx
    config: list[ConfigType] = hass.data[DATA_KNX_CONFIG][Platform.TIME]

    async_add_entities(KNXTime(xknx, entity_config) for entity_config in config)


def _create_xknx_device(xknx: XKNX, config: ConfigType) -> XknxDateTime:
    """Return a XKNX DateTime object to be used within XKNX."""
    return XknxDateTime(
        xknx,
        name=config[CONF_NAME],
        broadcast_type="TIME",
        localtime=False,
        group_address=config[KNX_ADDRESS],
        group_address_state=config.get(CONF_STATE_ADDRESS),
        respond_to_read=config[CONF_RESPOND_TO_READ],
        sync_state=config[CONF_SYNC_STATE],
    )


class KNXTime(KnxEntity, TimeEntity, RestoreEntity):
    """Representation of a KNX time."""

    _device: XknxDateTime

    def __init__(self, xknx: XKNX, config: ConfigType) -> None:
        """Initialize a KNX time."""
        super().__init__(_create_xknx_device(xknx, config))
        self._attr_entity_category = config.get(CONF_ENTITY_CATEGORY)
        self._attr_unique_id = str(self._device.remote_value.group_address)

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if (
            not self._device.remote_value.readable
            and (last_state := await self.async_get_last_state()) is not None
            and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        ):
            self._device.remote_value.value = time_time.strptime(
                last_state.state, _TIME_TRANSLATION_FORMAT
            )

    @property
    def native_value(self) -> dt_time | None:
        """Return the latest value."""
        if (time_struct := self._device.remote_value.value) is None:
            return None
        return dt_time(
            hour=time_struct.tm_hour,
            minute=time_struct.tm_min,
            second=min(time_struct.tm_sec, 59),  # account for leap seconds
        )

    async def async_set_value(self, value: dt_time) -> None:
        """Change the value."""
        time_struct = time_time.strptime(
            value.strftime(_TIME_TRANSLATION_FORMAT),
            _TIME_TRANSLATION_FORMAT,
        )
        await self._device.set(time_struct)
