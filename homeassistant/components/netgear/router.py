"""Represent the Netgear router and its devices."""
import logging
from datetime import timedelta
from homeassistant.util import dt as dt_util
from typing import Dict

from pynetgear import Netgear

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType

from .const import DEFAULT_CONSIDER_HOME, DEFAULT_METHOD_VERSION, DOMAIN
from .errors import CannotLoginException

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)


def get_api(
    password: str,
    host: str = None,
    username: str = None,
    port: int = None,
    ssl: bool = False,
    url: str = None,
) -> Netgear:
    """Get the Netgear API and login to it."""
    api: Netgear = Netgear(password, host, username, port, ssl, url)

    if not api.login():
        raise CannotLoginException

    return api


class NetgearRouter:
    """Representation of a Netgear router."""

    def __init__(self, hass: HomeAssistantType, entry: ConfigEntry) -> None:
        """Initialize a Netgear router."""
        self.hass = hass
        self._url = entry.data.get(CONF_URL)
        self._host = entry.data.get(CONF_HOST)
        self._port = entry.data.get(CONF_PORT)
        self._ssl = entry.data.get(CONF_SSL)
        self._username = entry.data.get(CONF_USERNAME)
        self._password = entry.data[CONF_PASSWORD]
        self._method_version = DEFAULT_METHOD_VERSION
        self._consider_home = DEFAULT_CONSIDER_HOME

        self._api: Netgear = None
        self._attrs = {}

        self.devices: Dict[str, any] = {}

        self._unsub_dispatcher = None
        self.listeners = []

    async def async_setup(self) -> None:
        """Set up a Netgear router."""
        self._api = await self.hass.async_add_executor_job(
            get_api,
            self._password,
            self._host,
            self._username,
            self._port,
            self._ssl,
            self._url,
        )

        await self.async_update_device_trackers()
        self._unsub_dispatcher = async_track_time_interval(
            self.hass, self.async_update_device_trackers, SCAN_INTERVAL
        )

    async def async_unload(self) -> None:
        """Unload a Netgear router."""
        self._unsub_dispatcher()
        self._unsub_dispatcher = None

    async def async_get_attached_devices(self) -> None:
        """Get the devices connected to the router."""
        if self._method_version == 1:
            return await self.hass.async_add_executor_job(
                self._api.get_attached_devices
            )

        return await self.hass.async_add_executor_job(
            self._api.get_attached_devices_2
        )

    async def async_update_device_trackers(self, now=None) -> None:
        """Update Netgear devices."""
        new_device = False
        ntg_devices: Dict[str, any] = await self.async_get_attached_devices()
        now = dt_util.utcnow()

        for ntg_device in ntg_devices:
            device_mac = ntg_device.mac

            if self._method_version == 2 and not ntg_device.link_rate:
                continue

            if not self.devices.get(device_mac):
                new_device = True

            self.devices[device_mac] = ntg_device._asdict()
            self.devices[device_mac]["last_seen"] = now

        for device in self.devices.values():
            if now - device["last_seen"] <= self._consider_home:
                device["active"] = True
            else:
                device["active"] = False

        async_dispatcher_send(self.hass, self.signal_device_update)

        if new_device:
            _LOGGER.debug("Netgear tracker: new device found")
            async_dispatcher_send(self.hass, self.signal_device_new)

    @property
    def signal_device_new(self) -> str:
        """Event specific per Netgear entry to signal new device."""
        return f"{DOMAIN}-{self._host}-device-new"

    @property
    def signal_device_update(self) -> str:
        """Event specific per Netgear entry to signal updates in devices."""
        return f"{DOMAIN}-{self._host}-device-update"
