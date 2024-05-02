"""Constants for Plugwise component."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Final, Literal

from homeassistant.const import Platform

DOMAIN: Final = "plugwise"

LOGGER = logging.getLogger(__package__)

API: Final = "api"
AVAILABLE_SCHEDULES: Final = "available_schedules"
DEVICES: Final = "devices"
FLOW_SMILE: Final = "smile (Adam/Anna/P1)"
FLOW_STRETCH: Final = "stretch (Stretch)"
FLOW_TYPE: Final = "flow_type"
GATEWAY: Final = "gateway"
MAC_ADDRESS: Final = "mac_address"
NONE: Final = "None"
OFF: Final = "off"
PW_TYPE: Final = "plugwise_type"
SELECT_SCHEDULE: Final = "select_schedule"
SMILE: Final = "smile"
STRETCH: Final = "stretch"
STRETCH_USERNAME: Final = "stretch"
ZIGBEE_MAC_ADDRESS: Final = "zigbee_mac_address"

PLATFORMS: Final[list[str]] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
ZEROCONF_MAP: Final[dict[str, str]] = {
    "smile": "Smile P1",
    "smile_thermo": "Smile Anna",
    "smile_open_therm": "Adam",
    "stretch": "Stretch",
}

NumberType = Literal[
    "maximum_boiler_temperature",
    "max_dhw_temperature",
    "temperature_offset",
]

SelectType = Literal[
    "select_dhw_mode",
    "select_gateway_mode",
    "select_regulation_mode",
    "select_schedule",
]
SelectOptionsType = Literal[
    "dhw_modes",
    "gateway_modes",
    "regulation_modes",
    "available_schedules",
]

# Default directives
DEFAULT_MAX_TEMP: Final = 30
DEFAULT_MIN_TEMP: Final = 4
DEFAULT_PORT: Final = 80
DEFAULT_SCAN_INTERVAL: Final[dict[str, timedelta]] = {
    "power": timedelta(seconds=10),
    "stretch": timedelta(seconds=60),
    "thermostat": timedelta(seconds=60),
}
DEFAULT_USERNAME: Final = "smile"

MASTER_THERMOSTATS: Final[list[str]] = [
    "thermostat",
    "thermostatic_radiator_valve",
    "zone_thermometer",
    "zone_thermostat",
]
