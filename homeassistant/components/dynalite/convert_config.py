"""Convert the HA config to the dynalite config."""

from typing import Any, Dict

from dynalite_devices_lib import const as dyn_const

from homeassistant.const import CONF_HOST

from .const import (
    CONF_ACTIVE,
    CONF_ACTIVE_INIT,
    CONF_ACTIVE_OFF,
    CONF_ACTIVE_ON,
    CONF_AREA,
    CONF_AUTO_DISCOVER,
    CONF_CHANNEL,
    CONF_CHANNEL_COVER,
    CONF_CHANNEL_TYPE,
    CONF_CLOSE_PRESET,
    CONF_DEFAULT,
    CONF_DEVICE_CLASS,
    CONF_DURATION,
    CONF_FADE,
    CONF_NAME,
    CONF_NO_DEFAULT,
    CONF_OPEN_PRESET,
    CONF_POLL_TIMER,
    CONF_PORT,
    CONF_PRESET,
    CONF_ROOM,
    CONF_ROOM_OFF,
    CONF_ROOM_ON,
    CONF_STOP_PRESET,
    CONF_TEMPLATE,
    CONF_TILT_TIME,
    CONF_TIME_COVER,
    LOGGER,
)

CONF_MAP = {
    CONF_ACTIVE: dyn_const.CONF_ACTIVE,
    CONF_ACTIVE_INIT: dyn_const.CONF_ACTIVE_INIT,
    CONF_ACTIVE_OFF: dyn_const.CONF_ACTIVE_OFF,
    CONF_ACTIVE_ON: dyn_const.CONF_ACTIVE_ON,
    CONF_AREA: dyn_const.CONF_AREA,
    CONF_AUTO_DISCOVER: dyn_const.CONF_AUTO_DISCOVER,
    CONF_CHANNEL: dyn_const.CONF_CHANNEL,
    CONF_CHANNEL_COVER: dyn_const.CONF_CHANNEL_COVER,
    CONF_CHANNEL_TYPE: dyn_const.CONF_CHANNEL_TYPE,
    CONF_CLOSE_PRESET: dyn_const.CONF_CLOSE_PRESET,
    CONF_DEFAULT: dyn_const.CONF_DEFAULT,
    CONF_DEVICE_CLASS: dyn_const.CONF_DEVICE_CLASS,
    CONF_DURATION: dyn_const.CONF_DURATION,
    CONF_FADE: dyn_const.CONF_FADE,
    CONF_HOST: dyn_const.CONF_HOST,
    CONF_NAME: dyn_const.CONF_NAME,
    CONF_NO_DEFAULT: dyn_const.CONF_NO_DEFAULT,
    CONF_OPEN_PRESET: dyn_const.CONF_OPEN_PRESET,
    CONF_POLL_TIMER: dyn_const.CONF_POLL_TIMER,
    CONF_PORT: dyn_const.CONF_PORT,
    CONF_PRESET: dyn_const.CONF_PRESET,
    CONF_ROOM: dyn_const.CONF_ROOM,
    CONF_ROOM_OFF: dyn_const.CONF_ROOM_OFF,
    CONF_ROOM_ON: dyn_const.CONF_ROOM_ON,
    CONF_STOP_PRESET: dyn_const.CONF_STOP_PRESET,
    CONF_TEMPLATE: dyn_const.CONF_TEMPLATE,
    CONF_TILT_TIME: dyn_const.CONF_TILT_TIME,
    CONF_TIME_COVER: dyn_const.CONF_TIME_COVER,
}


def convert_element(value: str) -> str:
    """Convert a string if it is in the map."""
    if value in CONF_MAP:
        LOGGER.error("XXX replaced %s with %s", value, CONF_MAP[value])
        return CONF_MAP[value]
    return value


def convert_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a config dict by replacing component consts with library consts."""
    result = {}
    for (key, value) in config.items():
        if isinstance(value, dict):
            new_value = convert_config(value)
        elif isinstance(value, str):
            new_value = convert_element(value)
        else:
            new_value = value
        result[convert_element(key)] = new_value
    return result
