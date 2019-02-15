"""
Support for DHT and DS18B20 sensors attached to a Konnected device.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.konnected/
"""
import logging

from homeassistant.components.konnected import (
    DOMAIN as KONNECTED_DOMAIN, SIGNAL_SENSOR_UPDATE)
from homeassistant.const import (
    CONF_DEVICES, CONF_PIN, CONF_TYPE, CONF_NAME, CONF_SENSORS,
    DEVICE_CLASS_HUMIDITY, DEVICE_CLASS_TEMPERATURE,
    ATTR_STATE, TEMP_FAHRENHEIT)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.util.temperature import celsius_to_fahrenheit

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['konnected']

SENSOR_TYPES = {
    DEVICE_CLASS_TEMPERATURE: ['Temperature', None],
    DEVICE_CLASS_HUMIDITY: ['Humidity', '%']
}


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up binary sensors attached to a Konnected device."""
    if discovery_info is None:
        return

    SENSOR_TYPES[DEVICE_CLASS_TEMPERATURE][1] = \
        hass.config.units.temperature_unit

    data = hass.data[KONNECTED_DOMAIN]
    device_id = discovery_info['device_id']
    sensors = []
    for sensor in filter(lambda s: s[CONF_TYPE] == 'dht',
                         data[CONF_DEVICES][device_id][CONF_SENSORS]):
        sensors.append(
            KonnectedDHTSensor(device_id, sensor, DEVICE_CLASS_TEMPERATURE))
        sensors.append(
            KonnectedDHTSensor(device_id, sensor, DEVICE_CLASS_HUMIDITY))

    async_add_entities(sensors)


class KonnectedDHTSensor(Entity):
    """Represents a Konnected DHT Sensor."""

    def __init__(self, device_id, data, sensor_type):
        """Initialize the entity for a single sensor_type."""
        self._data = data
        self._device_id = device_id
        self._type = sensor_type
        self._pin_num = self._data.get(CONF_PIN)
        self._state = self._data.get(ATTR_STATE)
        self._device_class = DEVICE_CLASS_TEMPERATURE
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self._name = '{} {}'.format(
            self._data.get(CONF_NAME, 'Konnected {} Pin {}'.format(
                device_id, self._pin_num)),
            SENSOR_TYPES[sensor_type][0])

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    async def async_added_to_hass(self):
        """Store entity_id and register state change callback."""
        self._data[self._type] = self.entity_id
        async_dispatcher_connect(
            self.hass, SIGNAL_SENSOR_UPDATE.format(self.entity_id),
            self.async_set_state)

    @callback
    def async_set_state(self, state):
        """Update the sensor's state."""
        state = float(state)
        if self._unit_of_measurement == TEMP_FAHRENHEIT:
            self._state = round(celsius_to_fahrenheit(state), 1)
        elif self._unit_of_measurement == '%':
            self._state = int(state)
        else:
            self._state = round(state, 1)
        self.async_schedule_update_ha_state()
