"""
Support for Insteon Hub.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/insteon_hub/
"""
import logging

import homeassistant.bootstrap as bootstrap
from homeassistant.const import (
    ATTR_DISCOVERED, ATTR_SERVICE, CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME,
    EVENT_PLATFORM_DISCOVERED, STATE_UNKNOWN, STATE_OFF, STATE_UNKNOWN,
    STATE_LOW, STATE_MED, STATE_HIGH, STATE_ON)
from homeassistant.helpers import validate_config
from homeassistant.helpers.entity import (Entity, ToggleEntity, LevelEntity)
from homeassistant.loader import get_component

DOMAIN = "insteon_hub"
DEVICE_CLASSES = ['light', 'fan', 'switch', 'sensor']
REQUIREMENTS = ['insteon_hub==0.4.5']
INSTEON = None
_LOGGER = logging.getLogger(__name__)
DISCOVERY = {
    'light': DOMAIN + '.light',
    'fan': DOMAIN + '.fan',
    'switch': DOMAIN + '.switch',
    'sensor': DOMAIN + '.sensor'}

def filter(devices, categories):
    categories = (categories  
        if isinstance(categories, list) 
        else [categories])
    matchingDevices = []
    for device in devices:
        if any( 
            device.DevCat == c['DevCat'] and 
            ('SubCat' not in c or device.SubCat in c['SubCat'])
            for c in  categories):
                matchingDevices.append(device)
    return matchingDevices

def setup(hass, config):
    """Setup Insteon Hub component.

    This will automatically import associated lights.
    """
    if not validate_config(
            config,
            {DOMAIN: [CONF_USERNAME, CONF_PASSWORD, CONF_API_KEY]},
            _LOGGER):
        return False

    import insteon

    username = config[DOMAIN][CONF_USERNAME]
    password = config[DOMAIN][CONF_PASSWORD]
    api_key = config[DOMAIN][CONF_API_KEY]

    global INSTEON
    INSTEON = insteon.Insteon(username, password, api_key)

    if INSTEON is None:
        _LOGGER.error("Could not connect to Insteon service.")
        return

    for deviceClass in DEVICE_CLASSES:
        component = get_component(deviceClass)
        bootstrap.setup_component(hass, component.DOMAIN, config)
        hass.bus.fire(
            EVENT_PLATFORM_DISCOVERED,
            { ATTR_SERVICE: DISCOVERY[deviceClass], ATTR_DISCOVERED: {}})
    return True

class InsteonDevice(Entity):
    """An abstract Class for an Insteon node."""

    def __init__(self, node):
        """Initialize the device."""
        self.node = node

    @property
    def name(self):
        """Return the name of the node."""
        return self.node.DeviceName

    @property
    def unique_id(self):
        """Return the ID of this insteon node."""
        return self.node.DeviceID

    def update(self):
        """Update state of the device."""
        pass

class InsteonSensorDevice(InsteonDevice, Entity):
    """An abstract Class for an Insteon node."""

    def __init__(self, node):
        super(InsteonSensorDevice, self).__init__(node)
        self._state = 0

    def update(self):
        """Update state of the sensor."""
        resp = self.node.send_command('get_relay_status', wait=True)
        try:
            _LOGGER.debug(str(resp))
            self._state = resp
        except KeyError:
            pass

class InsteonToggleDevice(InsteonDevice, ToggleEntity):
    """An abstract Class for an Insteon node."""

    def __init__(self, node):
        """Initialize the device."""
        super(InsteonToggleDevice, self).__init__(node)
        self._value = 0

    def update(self):
        """Update state of the sensor."""
        resp = self.node.send_command('get_status', wait=True)
        try:
            self._value = resp['response']['level']
        except KeyError:
            pass

    @property
    def is_on(self):
        """Return the boolean response if the node is on."""
        return self._value != 0

    def turn_on(self, **kwargs):
        """Turn device on."""
        self.node.send_command('on', { 'level':100 },  wait=True)
        self.update()

    def turn_off(self, **kwargs):
        """Turn device off."""
        self.node.send_command('off', wait=True)
        self.update()

class InsteonFanDevice(LevelEntity, InsteonDevice):
    """An abstract class for an Insteon node."""

    def __init__(self, node):
        super(InsteonFanDevice, self).__init__(node)
        self._value = STATE_UNKNOWN

    def update(self):
        """Update state of the sensor."""
        resp = self.node.send_command('get_status', wait=True)
        _LOGGER.error(str(resp))

    @property
    def state(self):
        """Get's the current fan speed."""
        return self._value;

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return ({
            'options': [
                {
                 'icon': 'mdi:block-helper',
                 'value': 'off',},
                {
                 'label': 'Low',
                 'value': 'low',},
                {
                 'label': 'Medium',
                 'value': 'med',},
                {
                 'label': 'High',
                 'value': 'high',},],
        })

    def set_level(self, level, **kwargs):
        """Set's the fan speed."""
        self.node.send_command('fan', {'speed': level}, wait=True)
        self._value = level
