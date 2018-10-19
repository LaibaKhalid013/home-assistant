"""
Support for monitoring a GreenEye Monitor energy monitor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/greeneye_monitor/
"""
import logging

import voluptuous as vol

from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    CONF_TEMPERATURE_UNIT,
    EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

REQUIREMENTS = ['greeneye_monitor==0.1']

_LOGGER = logging.getLogger(__name__)

CONF_CHANNELS = 'channels'
CONF_COUNTED_QUANTITY = 'counted_quantity'
CONF_COUNTED_QUANTITY_PER_PULSE = 'counted_quantity_per_pulse'
CONF_MONITOR_SERIAL_NUMBER = 'monitor'
CONF_MONITORS = 'monitors'
CONF_NET_METERING = 'net_metering'
CONF_NUMBER = 'number'
CONF_PULSE_COUNTERS = 'pulse_counters'
CONF_SERIAL_NUMBER = 'serial_number'
CONF_SENSORS = 'sensors'
CONF_SENSOR_TYPE = 'sensor_type'
CONF_TEMPERATURE_SENSORS = 'temperature_sensors'
CONF_TIME_UNIT = 'time_unit'

DATA_GREENEYE_MONITOR = 'greeneye_monitor'
DOMAIN = 'greeneye_monitor'

SENSOR_TYPE_CURRENT = 'current_sensor'
SENSOR_TYPE_PULSE_COUNTER = 'pulse_counter'
SENSOR_TYPE_TEMPERATURE = 'temperature_sensor'

TIME_UNIT_SECOND = 's'
TIME_UNIT_MINUTE = 'min'
TIME_UNIT_HOUR = 'h'

TEMPERATURE_SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_NUMBER): vol.Range(1, 8),
    vol.Required(CONF_NAME): cv.string,
})

TEMPERATURE_SENSORS_SCHEMA = vol.Schema({
    vol.Required(CONF_TEMPERATURE_UNIT): cv.temperature_unit,
    vol.Required(CONF_SENSORS): [TEMPERATURE_SENSOR_SCHEMA],
})

PULSE_COUNTER_SCHEMA = vol.Schema({
    vol.Required(CONF_NUMBER): vol.Range(1, 4),
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_COUNTED_QUANTITY): cv.string,
    vol.Optional(CONF_COUNTED_QUANTITY_PER_PULSE): vol.Coerce(float),
    vol.Optional(CONF_TIME_UNIT): vol.Any(
        TIME_UNIT_SECOND,
        TIME_UNIT_MINUTE,
        TIME_UNIT_HOUR),
})

PULSE_COUNTERS_SCHEMA = vol.Schema([PULSE_COUNTER_SCHEMA])

CHANNEL_SCHEMA = vol.Schema({
    vol.Required(CONF_NUMBER): vol.Range(1, 48),
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_NET_METERING): cv.boolean,
})

CHANNELS_SCHEMA = vol.Schema([CHANNEL_SCHEMA])

MONITOR_SERIAL_NUMBER_SCHEMA = vol.Schema({
    vol.Required(CONF_MONITOR_SERIAL_NUMBER): cv.positive_int,
})

MONITOR_SCHEMA = vol.Schema({
    vol.Required(CONF_SERIAL_NUMBER): cv.positive_int,
    vol.Optional(CONF_CHANNELS): CHANNELS_SCHEMA,
    vol.Optional(CONF_TEMPERATURE_SENSORS): TEMPERATURE_SENSORS_SCHEMA,
    vol.Optional(CONF_PULSE_COUNTERS): PULSE_COUNTERS_SCHEMA,
})

MONITORS_SCHEMA = vol.Schema([MONITOR_SCHEMA])

COMPONENT_SCHEMA = vol.Schema({
    vol.Required(CONF_PORT): cv.port,
    vol.Optional(CONF_MONITORS): MONITORS_SCHEMA,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: COMPONENT_SCHEMA,
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the GreenEye Monitor component."""
    from greeneye import Monitors

    monitors = Monitors()
    hass.data[DATA_GREENEYE_MONITOR] = monitors

    server_config = config[DOMAIN]
    server = await monitors.start_server(server_config[CONF_PORT])

    async def close_server(*args):
        """Close the monitoring server."""
        await server.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_server)

    for monitor_config in server_config.get(CONF_MONITORS, []):
        monitor_serial_number = {
            CONF_MONITOR_SERIAL_NUMBER: monitor_config[CONF_SERIAL_NUMBER],
        }

        channel_configs = monitor_config.get(CONF_CHANNELS, [])
        for channel_config in channel_configs:
            hass.async_add_job(async_load_platform(
                hass,
                'sensor',
                'greeneye_monitor',
                {
                    CONF_SENSOR_TYPE: SENSOR_TYPE_CURRENT,
                    **monitor_serial_number,
                    **channel_config,
                }))

        sensor_configs = \
            monitor_config.get(CONF_TEMPERATURE_SENSORS, {})
        if sensor_configs:
            temperature_unit = {
                CONF_TEMPERATURE_UNIT: sensor_configs[CONF_TEMPERATURE_UNIT],
            }
            for sensor_config in sensor_configs[CONF_SENSORS]:
                hass.async_add_job(async_load_platform(
                    hass,
                    'sensor',
                    'greeneye_monitor',
                    {
                        CONF_SENSOR_TYPE: SENSOR_TYPE_TEMPERATURE,
                        **monitor_serial_number,
                        **temperature_unit,
                        **sensor_config,
                    }))

        counter_configs = monitor_config.get(CONF_PULSE_COUNTERS, [])
        for counter_config in counter_configs:
            hass.async_add_job(async_load_platform(
                hass,
                'sensor',
                'greeneye_monitor',
                {
                    CONF_SENSOR_TYPE: SENSOR_TYPE_PULSE_COUNTER,
                    **monitor_serial_number,
                    **counter_config,
                }))
    return True
