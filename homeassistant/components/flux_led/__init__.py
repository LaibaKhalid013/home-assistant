"""The Flux LED/MagicLight integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Final

from flux_led import DeviceType
from flux_led.aio import AIOWifiLedBulb
from flux_led.const import (
    ATTR_ID,
    ATTR_REMOTE_ACCESS_ENABLED,
    ATTR_REMOTE_ACCESS_HOST,
    ATTR_REMOTE_ACCESS_PORT,
    ATTR_VERSION_NUM,
)
from flux_led.scanner import FluxLEDDiscovery

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.network import is_ip_address

from .const import (
    CONF_MINOR_VERSION,
    CONF_REMOTE_ACCESS_ENABLED,
    CONF_REMOTE_ACCESS_HOST,
    CONF_REMOTE_ACCESS_PORT,
    DISCOVER_SCAN_TIMEOUT,
    DOMAIN,
    FLUX_LED_DISCOVERY,
    FLUX_LED_EXCEPTIONS,
    SIGNAL_STATE_UPDATED,
    STARTUP_SCAN_TIMEOUT,
)
from .discovery import (
    async_discover_device,
    async_discover_devices,
    async_name_from_discovery,
    async_trigger_discovery,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS_BY_TYPE: Final = {
    DeviceType.Bulb: [Platform.LIGHT, Platform.NUMBER],
    DeviceType.Switch: [Platform.SWITCH],
}
DISCOVERY_INTERVAL: Final = timedelta(minutes=15)
REQUEST_REFRESH_DELAY: Final = 1.5


@callback
def async_wifi_bulb_for_host(host: str) -> AIOWifiLedBulb:
    """Create a AIOWifiLedBulb from a host."""
    return AIOWifiLedBulb(host)


async def async_update_entry_from_discovery(
    hass: HomeAssistant, entry: config_entries.ConfigEntry, device: FluxLEDDiscovery
) -> None:
    """Update a config entry from a flux_led discovery."""
    name = async_name_from_discovery(device)
    updates = {**entry.data}
    original_entry = {**entry.data}
    if ATTR_REMOTE_ACCESS_ENABLED in device:
        updates.update(
            {
                CONF_REMOTE_ACCESS_ENABLED: device[ATTR_REMOTE_ACCESS_ENABLED],
                CONF_REMOTE_ACCESS_HOST: device[ATTR_REMOTE_ACCESS_HOST],
                CONF_REMOTE_ACCESS_PORT: device[ATTR_REMOTE_ACCESS_PORT],
            }
        )
    if ATTR_VERSION_NUM in device:
        updates[CONF_MINOR_VERSION] = device[ATTR_VERSION_NUM]
    if not entry.data.get(CONF_NAME) or is_ip_address(entry.data[CONF_NAME]):
        updates[CONF_NAME] = async_name_from_discovery(device)
    mac_address = device[ATTR_ID]
    assert mac_address is not None
    updated = updates != original_entry
    hass.config_entries.async_update_entry(
        entry,
        data=updates,
        title=name,
        unique_id=dr.format_mac(mac_address),
    )
    if updated:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the flux_led component."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[FLUX_LED_DISCOVERY] = await async_discover_devices(
        hass, STARTUP_SCAN_TIMEOUT
    )

    async def _async_discovery(*_: Any) -> None:
        async_trigger_discovery(
            hass, await async_discover_devices(hass, DISCOVER_SCAN_TIMEOUT)
        )

    async_trigger_discovery(hass, domain_data[FLUX_LED_DISCOVERY])
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_discovery)
    async_track_time_interval(hass, _async_discovery, DISCOVERY_INTERVAL)
    return True


@callback
def _async_device_was_discovered(hass: HomeAssistant, mac: str) -> bool:
    """Check if a device was already discovered via a broadcast discovery."""
    discoveries: list[FluxLEDDiscovery] = hass.data[DOMAIN][FLUX_LED_DISCOVERY]
    return any(discovery for discovery in discoveries if discovery[ATTR_ID] == mac)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Flux LED/MagicLight from a config entry."""
    host = entry.data[CONF_HOST]
    if not entry.unique_id or not _async_device_was_discovered(hass, entry.unique_id):
        if discovery := await async_discover_device(hass, host):
            await async_update_entry_from_discovery(hass, entry, discovery)

    device: AIOWifiLedBulb = async_wifi_bulb_for_host(host)
    signal = SIGNAL_STATE_UPDATED.format(device.ipaddr)

    @callback
    def _async_state_changed(*_: Any) -> None:
        _LOGGER.debug("%s: Device state updated: %s", device.ipaddr, device.raw_state)
        async_dispatcher_send(hass, signal)

    try:
        await device.async_setup(_async_state_changed)
    except FLUX_LED_EXCEPTIONS as ex:
        raise ConfigEntryNotReady(
            str(ex) or f"Timed out trying to connect to {device.ipaddr}"
        ) from ex

    coordinator = FluxLedUpdateCoordinator(hass, device, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    platforms = PLATFORMS_BY_TYPE[device.device_type]
    hass.config_entries.async_setup_platforms(entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    device: AIOWifiLedBulb = hass.data[DOMAIN][entry.entry_id].device
    platforms = PLATFORMS_BY_TYPE[device.device_type]
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, platforms):
        del hass.data[DOMAIN][entry.entry_id]
        await device.async_stop()
    return unload_ok


class FluxLedUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to gather data for a specific flux_led device."""

    def __init__(
        self, hass: HomeAssistant, device: AIOWifiLedBulb, entry: ConfigEntry
    ) -> None:
        """Initialize DataUpdateCoordinator to gather data for specific device."""
        self.device = device
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=self.device.ipaddr,
            update_interval=timedelta(seconds=10),
            # We don't want an immediate refresh since the device
            # takes a moment to reflect the state change
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )

    async def _async_update_data(self) -> None:
        """Fetch all device and sensor data from api."""
        try:
            await self.device.async_update()
        except FLUX_LED_EXCEPTIONS as ex:
            raise UpdateFailed(ex) from ex
