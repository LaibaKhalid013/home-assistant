"""Support for Repetier-Server sensors."""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (
    CONF_API_KEY, CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_PORT,
    CONF_SENSORS, TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import slugify as util_slugify

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'RepetierServer'
DOMAIN = 'repetier'
REPETIER_API = 'repetier_api'
SCAN_INTERVAL = timedelta(seconds=10)
UPDATE_SIGNAL = 'repetier_update_signal'


def has_all_unique_names(value):
    """Validate that printers have an unique name."""
    names = [util_slugify(printer[CONF_NAME]) for printer in value]
    vol.Schema(vol.Unique())(names)
    return value


SENSOR_TYPES = {
    # Type, Unit, Icon
    'bed_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                        '_bed_'],
    'extruder_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                             '_extruder_'],
    'chamber_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                            '_chamber_'],
    'current_state': ['state', None, 'mdi:printer-3d', ''],
    'current_job': ['progress', '%', 'mdi:file-percent', '_current_job'],
    'time_remaining': ['progress', None, 'mdi:clock-end', '_remaining'],
    'time_elapsed': ['progress', None, 'mdi:clock-start', '_elapsed'],
}

SENSOR_SCHEMA = vol.Schema({
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=3344): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SENSORS, default={}): SENSOR_SCHEMA,
    })], has_all_unique_names),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Repetier Server component."""
    import pyrepetier

    hass.data[REPETIER_API] = {}
    sensor_info = []

    for repetier in config[DOMAIN]:
        _LOGGER.debug("Repetier server config %s", repetier[CONF_HOST])

        url = "http://{}".format(repetier[CONF_HOST])
        port = repetier[CONF_PORT]
        api_key = repetier[CONF_API_KEY]

        client = pyrepetier.Repetier(
            url=url,
            port=port,
            apikey=api_key)

        printers = client.getprinters()

        if not printers:
            return False

        api = PrinterAPI(hass, client, printers)
        api.update()
        track_time_interval(hass, api.update, SCAN_INTERVAL)

        hass.data[REPETIER_API][repetier[CONF_NAME]] = api

        sensors = repetier[CONF_SENSORS][CONF_MONITORED_CONDITIONS]
        for pidx, printer in enumerate(printers):
            for sensor_type in sensors:
                sensvar = {}
                sensvar['sensor_type'] = sensor_type
                sensvar['printer_id'] = pidx
                sensvar['name'] = printer.slug
                sensvar['printer_name'] = repetier[CONF_NAME]

                if sensor_type == 'bed_temperature':
                    if printer.heatedbeds is None:
                        continue
                    for idx, _ in enumerate(printer.heatedbeds):
                        sensvar['data_key'] = idx
                        sensor_info.append(sensvar)
                elif sensor_type == 'extruder_temperature':
                    if printer.extruder is None:
                        continue
                    for idx, _ in enumerate(printer.extruder):
                        sensvar['data_key'] = idx
                        sensor_info.append(sensvar)
                elif sensor_type == 'chamber_temperature':
                    if printer.heatedchambers is None:
                        continue
                    for idx, _ in enumerate(printer.heatedchambers):
                        sensvar['data_key'] = idx
                        sensor_info.append(sensvar)
                else:
                    sensvar['data_key'] = None
                    sensor_info.append(sensvar)

    load_platform(hass, 'sensor', DOMAIN, sensor_info, config)

    return True


API_SENSOR_METHODS = {
    'bed_temperature': {
        'online': ['heatedbeds', 'state'],
        'state': {'heatedbeds': 'data_key'},
        'data_key': {
            'tempset': 'temp_set',
            'tempread': 'temp',
            'output': 'output'
        },
    },
}


class PrinterAPI:
    """Handle the printer API."""

    def __init__(self, hass, client, printers):
        """Set up instance."""
        self._hass = hass
        self._client = client
        self.printers = printers

    def get_data(self, printer_id, sensor_type, data_key):
        """Get data from the state cache."""
        printer = self.printers[printer_id]
        methods = API_SENSOR_METHODS[sensor_type]
        for prop in methods['online']:
            online = getattr(printer, prop)
            if online is None:
                return None

        data = {}
        for prop, attr in methods['state'].items():
            prop_data = getattr(printer, prop)
            if attr == 'data_key':
                dk_props = methods['data_key']
                for dk_prop, dk_attr in dk_props.items():
                    data[dk_attr] = getattr(prop_data[data_key], dk_prop)
            else:
                data[attr] = prop_data
        return data

    def update(self, now=None):
        """Update the state cache from the printer API."""
        for printer in self.printers:
            printer.get_data()
        dispatcher_send(self._hass, UPDATE_SIGNAL)
