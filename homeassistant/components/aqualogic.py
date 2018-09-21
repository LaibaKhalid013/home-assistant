"""
Support for AquaLogic component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/aqualogic/
"""
from datetime import timedelta
import logging
import time
import threading
import socket

import voluptuous as vol

from homeassistant.const import (
    CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
)
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = ["aqualogic==0.9", "zope.event==4.3.0"]

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aqualogic"
UPDATE_TOPIC = DOMAIN + "_update"
CONF_UNIT = "unit"
RECONNECT_INTERVAL = timedelta(seconds=10)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, base_config):
    """Setup AquaLogic platform."""
    config = base_config.get(DOMAIN)

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    hass.data[DOMAIN] = AquaLogicProcessor(hass, host, port)

    return True

class AquaLogicProcessor(threading.Thread):
    def __init__(self, hass, host, port):
        super(AquaLogicProcessor, self).__init__(daemon=True)
        self._hass = hass
        self._host = host
        self._port = port
        self._shutdown = False
        self._panel = None

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START,
                             self.start_listen)
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
                             self.shutdown)
        _LOGGER.debug("AquaLogicProcessor %s:%i initialized",
                      self._host, self._port)

    def start_listen(self, event):
        """Start event-processing thread."""
        _LOGGER.debug("Event processing thread started")
        self.start()

    def shutdown(self, event):
        """Signal shutdown of processing event."""
        _LOGGER.debug("Event processing signaled exit")
        self._shutdown = True

    def data_changed(self, panel):
        self._hass.helpers.dispatcher.dispatcher_send(UPDATE_TOPIC)

    def run(self):
        from aqualogic.core import AquaLogic
        import zope.event

        zope.event.subscribers.append(self.data_changed)
        while True:
            try:
                s = socket.create_connection((self._host, self._port), 10)

                reader = s.makefile(mode='rb')
                writer = s.makefile(mode='wb')

                self._panel = AquaLogic(reader, writer)
                self._panel.process()

                if self._shutdown:
                    return

                _LOGGER.error("Connection to %s:%d lost",
                              self._host, self._port)
            except socket.timeout:
                _LOGGER.error("Connection to %s:%d timed out",
                              self._host, self._port)
            except Exception:
                _LOGGER.exception("Error")
                time.sleep(RECONNECT_INTERVAL.seconds)

    @property
    def panel(self):
        return self._panel
