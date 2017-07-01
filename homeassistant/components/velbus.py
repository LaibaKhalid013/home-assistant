"""
Support for Velbus platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/velbus/
"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, \
                                CONF_PORT

REQUIREMENTS = ['python-velbus==2.0.7']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'velbus'


VELBUS_MESSAGE = 'velbus.message'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PORT): cv.string,
})


def setup(hass, config):
    """Set up the Velbus platform."""
    import velbus
    port = config[DOMAIN][CONF_PORT]
    connection = velbus.VelbusUSBConnection(port)
    controller = velbus.Controller(connection)
    hass.data['VelbusController'] = controller

    @callback
    def stop_velbus(event):
        """Disconnect from serial port."""
        _LOGGER.debug("Shutting down ")
        connection.stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_velbus)
    return True
