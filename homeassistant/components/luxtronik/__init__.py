"""Support for Luxtronik heatpump controllers."""
from datetime import timedelta
import logging

from luxtronik import LOGGER as LuxLogger, Luxtronik as Lux
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

LuxLogger.setLevel(level="WARNING")


_LOGGER = logging.getLogger(__name__)

ATTR_PARAMETER = "parameter"
ATTR_VALUE = "value"

CONF_INVERT_STATE = "invert"
CONF_SAFE = "safe"
CONF_GROUP = "group"
CONF_PARAMETERS = "parameters"
CONF_CALCULATIONS = "calculations"
CONF_VISIBILITIES = "visibilities"

CONF_CELSIUS = "celsius"
CONF_SECONDS = "seconds"
CONF_PULSES = "pulses"
CONF_IPADDRESS = "ipaddress"
CONF_TIMESTAMP = "timestamp"
CONF_ERRORCODE = "errorcode"
CONF_KELVIN = "kelvin"
CONF_BAR = "bar"
CONF_PERCENT = "percent"
CONF_RPM = "rpm"
CONF_ENERGY = "energy"
CONF_VOLTAGE = "voltage"
CONF_HOURS = "hours"
CONF_FLOW = "flow"
CONF_LEVEL = "level"
CONF_COUNT = "count"
CONF_VERSION = "version"

TIME_SECONDS = "s"
TIME_HOUR = "h"
TEMP_KELVIN = "K"
PERCENTAGE_PERCENT = "%"
VOLTAGE_VOLT = "V"
FLOW_LITERS_PER_MINUTE = "l/min"

DATA_LUXTRONIK = "DATA_LT"

LUXTRONIK_PLATFORMS = ["binary_sensor", "sensor"]
DOMAIN = "luxtronik"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

SERVICE_WRITE = "write"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_PORT, default=8889): cv.port,
                vol.Optional(CONF_SAFE, default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_WRITE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PARAMETER): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.Number, cv.string),
    }
)


def setup(hass, config):
    """Set up the Luxtronik component."""
    conf = config[DOMAIN]

    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    safe = conf.get(CONF_SAFE)

    luxtronik = Luxtronik(host, port, safe)
    luxtronik.update()

    hass.data[DATA_LUXTRONIK] = luxtronik

    def write_parameter(service):
        """Write a parameter to the Luxtronik heatpump."""
        parameter = service.data.get(ATTR_PARAMETER)
        value = service.data.get(ATTR_VALUE)
        luxtronik.write(parameter, value)

    hass.services.register(
        DOMAIN, SERVICE_WRITE, write_parameter, schema=SERVICE_WRITE_SCHEMA
    )

    return True


class Luxtronik:
    """Handle all communication with Luxtronik."""

    def __init__(self, host, port, safe=True):
        """Initialize the Luxtronik connection."""

        self._host = host
        self._port = port
        self._luxtronik = Lux(host, port, safe)
        self.update()

    def get_sensor(self, group, sensor_id):
        """Get sensor by configured sensor ID."""
        sensor = None
        if group == CONF_PARAMETERS:
            sensor = self._luxtronik.parameters.get(sensor_id)
        if group == CONF_CALCULATIONS:
            sensor = self._luxtronik.calculations.get(sensor_id)
        if group == CONF_VISIBILITIES:
            sensor = self._luxtronik.visibilities.get(sensor_id)
        return sensor

    def write(self, parameter, value):
        """Write a parameter to the Luxtronik heatpump."""
        self._luxtronik.parameters.set(parameter, value)
        self._luxtronik.write()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the data from Luxtronik."""
        self._luxtronik.read()
