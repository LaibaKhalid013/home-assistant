"""
Support to use FortiOS device like FortiGate as device tracker.

This component is part of the device_tracker platform.
"""
import logging

from fortiosapi import FortiOSAPI
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_TOKEN, CONF_VERIFY_SSL
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
DEFAULT_VERIFY_SSL = False


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    }
)


def get_scanner(hass, config):
    """Validate the configuration and return a FortiOSDeviceScanner."""
    host = config[DOMAIN][CONF_HOST]
    verify_ssl = config[DOMAIN][CONF_VERIFY_SSL]
    token = config[DOMAIN][CONF_TOKEN]

    fgt = FortiOSAPI()

    try:
        fgt.tokenlogin(host, token, verify_ssl)
    except ConnectionError as ex:
        _LOGGER.error("ConnectionError to FortiOS API: %s", ex)
        return None
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.error("Failed to login to FortiOS API: %s", ex)
        return None

    status_json = fgt.monitor("system/status", "")
    version = status_json["version"][1:]
    _LOGGER.debug("FortiOS version: %s", version)

    fos_major, fos_minor, fos_patch = [int(x, 10) for x in version.split(".")]

    if (
        fos_major < 6
        or (fos_major == 6 and fos_minor < 4)
        or (fos_major == 6 and fos_minor == 4 and fos_patch < 3)
    ):
        _LOGGER.error(
            "Unsupported FortiOS version :  %s. \
            Version 6.4.3 and newer are supported",
            version
        )
        return None

    return FortiOSDeviceScanner(fgt)


class FortiOSDeviceScanner(DeviceScanner):
    """This class queries a FortiOS unit for connected devices."""

    def __init__(self, fgt) -> None:
        """Initialize the scanner."""
        self._clients = {}
        self._clients_json = {}
        self._fgt = fgt

    def update(self):
        """Update clients from the device."""
        clients_json = self._fgt.monitor("user/device/query", "")
        self._clients_json = clients_json

        self._clients = []

        if clients_json:
            try:
                for client in clients_json["results"]:
                    if client["is_online"]:
                        self._clients.append(client["mac"].upper())
            except KeyError as kex:
                _LOGGER.error("Key not found in clients: %s", kex)

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self.update()
        return self._clients

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        _LOGGER.debug("Getting name of device %s", device)

        device = device.lower()

        if (data := self._clients_json) == 0:
            _LOGGER.error("No json results to get device names")
            return None

        for client in data["results"]:
            if client["mac"] == device:
                try:
                    name = client["hostname"]
                    _LOGGER.debug("Getting device name=%s", name)
                    return name
                except KeyError as kex:
                    _LOGGER.debug(
                        "No hostname found for %s in \
                    client data: %s",
                    device,
                    kex
                    )
                    return device.replace(":", "_")

        return None
