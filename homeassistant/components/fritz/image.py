"""FRITZ image integration."""

from __future__ import annotations

from io import BytesIO
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util, slugify

from .common import AvmWrapper, FritzBoxBaseEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up guest WiFi QR code for device."""
    avm_wrapper: AvmWrapper = hass.data[DOMAIN][entry.entry_id]

    guest_wifi_info = await hass.async_add_executor_job(
        avm_wrapper.fritz_guest_wifi.get_info
    )

    if not guest_wifi_info.get("NewEnable"):
        return

    async_add_entities(
        [FritzGuestWifiQRImage(avm_wrapper, entry.title, guest_wifi_info["NewSSID"])]
    )


class FritzGuestWifiQRImage(FritzBoxBaseEntity, ImageEntity):
    """Implementation of the FritzBox guest wifi QR code image entity."""

    _attr_content_type = "image/png"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, avm_wrapper: AvmWrapper, device_friendly_name: str, ssid: str
    ) -> None:
        """Initialize the image entity."""
        self._attr_name = f"{device_friendly_name} {ssid} QR-Code"
        self._attr_unique_id = slugify(f"{avm_wrapper.unique_id}-{ssid}-qr-code")
        self._current_qr_bytes: bytes | None = None
        super().__init__(avm_wrapper, device_friendly_name)
        ImageEntity.__init__(self)

    async def async_added_to_hass(self) -> None:
        """Set the update time."""
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes:
        """Return bytes of image."""
        qr_stream: BytesIO = await self.hass.async_add_executor_job(
            self._avm_wrapper.fritz_guest_wifi.get_wifi_qr_code, "png"
        )
        qr_bytes = qr_stream.getvalue()

        _LOGGER.debug("fetched %s bytes", len(qr_bytes))

        if self._current_qr_bytes is None:
            self._current_qr_bytes = qr_bytes

        if self._current_qr_bytes != qr_bytes:
            dt_now = dt_util.utcnow()
            _LOGGER.debug("qr code has changed, reset image last updated property")
            self._attr_image_last_updated = dt_now
            self._current_qr_bytes = qr_bytes
            self.async_write_ha_state()

        return qr_bytes
