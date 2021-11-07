"""Support for KNX/IP buttons."""
from __future__ import annotations

from xknx import XKNX
from xknx.devices import RawValue as XknxRawValue
from xknx.dpt import DPTBase

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_ENTITY_CATEGORY, CONF_NAME, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, KNX_ADDRESS
from .knx_entity import KnxEntity
from .schema import ButtonSchema


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up buttons for KNX platform."""
    if not discovery_info or not discovery_info["platform_config"]:
        return
    platform_config = discovery_info["platform_config"]
    xknx: XKNX = hass.data[DOMAIN].xknx

    async_add_entities(
        KNXButton(xknx, entity_config) for entity_config in platform_config
    )


class KNXButton(KnxEntity, ButtonEntity):
    """Representation of a KNX button."""

    _device: XknxRawValue

    def __init__(self, xknx: XKNX, config: ConfigType) -> None:
        """Initialize of KNX switch."""
        if (_type := config.get(CONF_TYPE)) and (
            transcoder := DPTBase.parse_transcoder(_type)
        ):
            payload_length = transcoder.payload_length
            self._payload = int.from_bytes(
                transcoder.to_knx(config[ButtonSchema.CONF_PAYLOAD]), byteorder="big"
            )
        else:
            payload_length = config[ButtonSchema.CONF_PAYLOAD_LENGTH]
            self._payload = config[ButtonSchema.CONF_PAYLOAD]
        super().__init__(
            device=XknxRawValue(
                xknx,
                name=config[CONF_NAME],
                payload_length=payload_length,
                group_address=config[KNX_ADDRESS],
            )
        )
        self._attr_entity_category = config.get(CONF_ENTITY_CATEGORY)
        self._attr_unique_id = str(self._device.remote_value.group_address)

    async def async_press(self) -> None:
        """Press the button."""
        await self._device.set(self._payload)
