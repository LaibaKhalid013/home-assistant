"""Config flow for govee_ble integration."""
from __future__ import annotations

from homeassistant.components.bluetooth.config_flow import BluetoothConfigFlow

from .const import DOMAIN
from .data import GoveeBluetoothDeviceData


class GoveeBluetoothConfigFlow(BluetoothConfigFlow, domain=DOMAIN):
    """Handle a config flow for govee_ble."""

    DEVICE_DATA_CLASS = GoveeBluetoothDeviceData
