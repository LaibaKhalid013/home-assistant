"""Support for Fronius devices."""
import logging
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_RESOURCE, CONF_SENSOR_TYPE, CONF_DEVICE, CONF_MONITORED_CONDITIONS
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_SCOPE = 'scope'

TYPE_INVERTER = 'inverter'
TYPE_STORAGE = 'storage'
TYPE_METER = 'meter'
TYPE_POWER_FLOW = 'power_flow'
SCOPE_DEVICE = 'device'
SCOPE_SYSTEM = 'system'

DEFAULT_SCOPE = SCOPE_DEVICE
DEFAULT_DEVICE = 0

SENSOR_TYPES = [TYPE_INVERTER, TYPE_STORAGE, TYPE_METER, TYPE_POWER_FLOW]
SCOPE_TYPES = [SCOPE_DEVICE, SCOPE_SYSTEM]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Required(CONF_MONITORED_CONDITIONS):
        vol.All(cv.ensure_list, [{
            vol.Required(CONF_SENSOR_TYPE): vol.In(SENSOR_TYPES),
            vol.Optional(CONF_SCOPE, default=DEFAULT_SCOPE): vol.In(SCOPE_TYPES),
            vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE):
                cv.positive_int,
        }]),
})


async def async_setup_platform(hass,
                               config,
                               async_add_devices,
                               discovery_info=None):
    """Set up of Fronius platform."""
    from pyfronius import Fronius

    session = async_get_clientsession(hass)
    fronius = Fronius(session, config[CONF_RESOURCE])

    sensors = []
    for condition in config[CONF_MONITORED_CONDITIONS]:

        name = "fronius_{}_{}".format(
            condition[CONF_SENSOR_TYPE], config[CONF_RESOURCE]
        )
        device = condition.get(CONF_DEVICE)
        if device == 0:
            if condition[CONF_SENSOR_TYPE] == 'inverter':
                device = 1
        name = "{}_{}".format(name, device)

        sensor = FroniusSensor(fronius, name, condition[CONF_SENSOR_TYPE],
                               condition.get(CONF_SCOPE), device)
        sensors.append(sensor)

    async_add_devices(sensors)


class FroniusSensor(Entity):
    """The Fronius sensor implementation."""

    def __init__(self, data, name, device_type, scope, device):
        """Initialize the sensor."""
        self.data = data
        self._name = name
        self._type = device_type
        self._device = device
        self._scope = scope
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_update(self):
        """Retrieve and update latest state."""
        values = {}
        try:
            values = await self._update()
        except ConnectionError:
            _LOGGER.error("Failed to update: connection error.")
        except ValueError:
            _LOGGER.error(
                "Failed to update: invalid response returned."
            )

        if values:
            self._state = values['status']['Code']
            attributes = {}
            for key in values:
                if 'value' in values[key] and values[key]['value']:
                    attributes[key] = values[key]['value']
                else:
                    attributes[key] = 0
            self._attributes = attributes

    async def _update(self):
        """Get the values for the current state."""
        if self._type == TYPE_INVERTER:
            if self._scope == SCOPE_SYSTEM:
                return await self.data.current_system_inverter_data()
            return await self.data.current_inverter_data(self._device)
        if self._type == TYPE_STORAGE:
            return await self.data.current_storage_data(self._device)
        if self._type == TYPE_METER:
            if self._scope == SCOPE_SYSTEM:
                return await self.data.current_system_meter_data()
            return await self.data.current_meter_data()
        if self._type == TYPE_POWER_FLOW:
            return await self.data.current_power_flow()
