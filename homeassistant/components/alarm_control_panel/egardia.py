"""
Interfaces with Egardia/Woonveilig alarm control panel.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.egardia/
"""
import logging

import requests
import voluptuous as vol

import homeassistant.components.alarm_control_panel as alarm
import homeassistant.exceptions as exc
import homeassistant.helpers.config_validation as cv
from homeassistant.components.alarm_control_panel import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_PORT, CONF_HOST, CONF_PASSWORD, CONF_USERNAME, STATE_UNKNOWN,
    CONF_NAME, STATE_ALARM_DISARMED, STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_TRIGGERED)

REQUIREMENTS = ['pythonegardia==1.0.25']

_LOGGER = logging.getLogger(__name__)

CONF_REPORT_SERVER_CODES = 'report_server_codes'
CONF_REPORT_SERVER_ENABLED = 'report_server_enabled'
CONF_REPORT_SERVER_PORT = 'report_server_port'
CONF_REPORT_SERVER_CODES_IGNORE = 'ignore'
CONF_VERSION = 'version'

DEFAULT_NAME = 'Egardia'
DEFAULT_PORT = 80
DEFAULT_REPORT_SERVER_ENABLED = False
DEFAULT_REPORT_SERVER_PORT = 52010
DEFAULT_VERSION = 'GATE-01'
DOMAIN = 'egardia'

NOTIFICATION_ID = 'egardia_notification'
NOTIFICATION_TITLE = 'Egardia'

STATES = {
    'ARM': STATE_ALARM_ARMED_AWAY,
    'DAY HOME': STATE_ALARM_ARMED_HOME,
    'DISARM': STATE_ALARM_DISARMED,
    'HOME': STATE_ALARM_ARMED_HOME,
    'TRIGGERED': STATE_ALARM_TRIGGERED,
    'UNKNOWN': STATE_UNKNOWN,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Optional(CONF_VERSION, default=DEFAULT_VERSION): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_REPORT_SERVER_CODES): vol.All(cv.ensure_list),
    vol.Optional(CONF_REPORT_SERVER_ENABLED,
                 default=DEFAULT_REPORT_SERVER_ENABLED): cv.boolean,
    vol.Optional(CONF_REPORT_SERVER_PORT, default=DEFAULT_REPORT_SERVER_PORT):
        cv.port,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Egardia platform."""
    from pythonegardia import egardiadevice
    from pythonegardia import egardiaserver

    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    rs_enabled = config.get(CONF_REPORT_SERVER_ENABLED)
    rs_port = config.get(CONF_REPORT_SERVER_PORT)
    rs_codes = config.get(CONF_REPORT_SERVER_CODES)
    version = config.get(CONF_VERSION)

    try:
        egardiasystem = egardiadevice.EgardiaDevice(
            host, port, username, password, '', version)
    except requests.exceptions.RequestException:
        raise exc.PlatformNotReady()
    except egardiadevice.UnauthorizedError:
        _LOGGER.error("Unable to authorize. Wrong password or username")
        return False

    if rs_enabled:
        # Set up the egardia server
        _LOGGER.info("Setting up EgardiaServer")
        try:
            egardiaserver = egardiaserver.EgardiaServer('', rs_port)
            bound = egardiaserver.bind()
            if not bound:
                raise IOError("Binding error occurred while " +
                              "starting EgardiaServer")
        except IOError as ioe:
            errormessage = "Unable to start EgardiaServer: ", ioe.message
            _LOGGER.error(errormessage)
            return False

    add_devices([EgardiaAlarm(
        name, egardiasystem, hass, egardiaserver, rs_codes)], True)


class EgardiaAlarm(alarm.AlarmControlPanel):
    """Representation of a Egardia alarm."""

    def __init__(self, name, egardiasystem, hass, egardiaserver=None,
                 rs_codes=None):
        """Initialize object."""
        self._name = name
        self._egardiasystem = egardiasystem
        self._status = STATE_UNKNOWN
        self._egardiaserver = egardiaserver
        self._hass = hass

        if rs_codes is not None:
            self._rs_codes = rs_codes[0]
        else:
            self._rs_codes = rs_codes

        if self._egardiaserver is not None:
            _LOGGER.info("Starting EgardiaServer and registering callback")
            # Register callback for alarm status changes through EgardiaServer
            self._egardiaserver.register_callback(self.status_callback)
            self._egardiaserver.start()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._status

    @property
    def should_poll(self):
        """Poll if no report server is enabled."""
        if self._egardiaserver is None:
            return True
        return False

    def handle_system_status_event(self, event):
        """Handle egardia_system_status_event."""
        if event.get('status') is not None:
            statuscode = event.get('status')
            status = self.lookupstatusfromcode(statuscode)
            self.parsestatus(status)
            self.schedule_update_ha_state()

    def status_callback(self, event):
        """Callback function for status passed from EgardiaServer."""
        if event is not None:
            self.handle_system_status_event(event)

    def lookupstatusfromcode(self, statuscode):
        """Look at the rs_codes and returns the status from the code."""
        status = 'UNKNOWN'
        if self._rs_codes is not None:
            statuscode = str(statuscode).strip()
            for i in self._rs_codes:
                val = str(self._rs_codes[i]).strip()
                if ',' in val:
                    splitted = val.split(',')
                    for code in splitted:
                        code = str(code).strip()
                        if statuscode == code:
                            status = i.upper()
                            break
                elif statuscode == val:
                    status = i.upper()
                    break
        return status

    def parsestatus(self, status):
        """Parse the status."""
        _LOGGER.debug("Parsing status %s", status)
        # Ignore the statuscode if it is IGNORE
        if status.lower().strip() != CONF_REPORT_SERVER_CODES_IGNORE:
            _LOGGER.debug("Not ignoring status")
            newstatus = ([v for k, v in STATES.items()
                          if status.upper() == k][0])
            self._status = newstatus
        else:
            _LOGGER.error("Ignoring status")

    def update(self):
        """Update the alarm status."""
        status = self._egardiasystem.getstate()
        self.parsestatus(status)

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        try:
            self._egardiasystem.alarm_disarm()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Egardia device exception occurred when "
                          "sending disarm command: %s", err)

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        try:
            self._egardiasystem.alarm_arm_home()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Egardia device exception occurred when "
                          "sending arm home command: %s", err)

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        try:
            self._egardiasystem.alarm_arm_away()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Egardia device exception occurred when "
                          "sending arm away command: %s", err)
