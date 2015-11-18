#!/usr/local/bin/python3
"""
homeassistant.components.thermostat.ecobee
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ecobee Thermostat Component

This component adds support for Ecobee3 Wireless Thermostats.
You will need to setup developer access to your thermostat,
and create and API key on the ecobee website.

The first time you run this component you will see a configuration
component card in Home Assistant.  This card will contain a PIN code
that you will need to use to authorize access to your thermostat.  You
can do this at https://www.ecobee.com/consumerportal/index.html
Click My Apps, Add application, Enter Pin and click Authorize.

After authorizing the application click the button in the configuration
card.  Now your thermostat should shown in home-assistant.  Once the
thermostat has been added you can add the ecobee sensor component
to your configuration.yaml.

thermostat:
  platform: ecobee
  api_key: asdfasdfasdfasdfasdfaasdfasdfasdfasdf
"""
from homeassistant.loader import get_component
from homeassistant.components.thermostat import (ThermostatDevice, STATE_COOL,
                                                 STATE_IDLE, STATE_HEAT)
from homeassistant.const import (
    CONF_API_KEY, TEMP_FAHRENHEIT, STATE_ON, STATE_OFF)
from homeassistant.util import Throttle
from datetime import timedelta
import logging
import os

REQUIREMENTS = [
    'https://github.com/nkgilley/python-ecobee-api/archive/'
    '790c20d820dbb727af2dbfb3ef0f79231e19a503.zip#python-ecobee==0.0.1']

_LOGGER = logging.getLogger(__name__)

ECOBEE_CONFIG_FILE = 'ecobee.conf'
_CONFIGURING = {}

# Return cached results if last scan was less then this time ago
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=180)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Setup Platform """
    # Only act if we are not already configuring this host
    if 'ecobee' in _CONFIGURING:
        return

    from pyecobee import config_from_file

    # Create ecobee.conf if it doesn't exist
    if not os.path.isfile(hass.config.path(ECOBEE_CONFIG_FILE)):
        jsonconfig = {"API_KEY": config[CONF_API_KEY]}
        config_from_file(hass.config.path(ECOBEE_CONFIG_FILE), jsonconfig)
    data = EcobeeData(hass.config.path(ECOBEE_CONFIG_FILE))
    setup_ecobee(hass, data, config, add_devices_callback)


def setup_ecobee(hass, data, config, add_devices_callback):
    """ Setup ecobee thermostat """
    # If ecobee has a PIN then it needs to be configured.
    if data.ecobee.pin is not None:
        request_configuration(data, hass, add_devices_callback)
        return

    if 'ecobee' in _CONFIGURING:
        configurator = get_component('configurator')
        configurator.request_done(_CONFIGURING.pop('ecobee'))

    add_devices_callback(Thermostat(data, index)
                         for index in range(len(data.ecobee.thermostats)))


def request_configuration(data, hass, add_devices_callback):
    """ Request configuration steps from the user. """
    configurator = get_component('configurator')
    if 'ecobee' in _CONFIGURING:
        configurator.notify_errors(
            _CONFIGURING['ecobee'], "Failed to register, please try again.")

        return

    # pylint: disable=unused-argument
    def ecobee_configuration_callback(callback_data):
        """ Actions to do when our configuration callback is called. """
        data.ecobee.request_tokens()
        data.ecobee.update()
        setup_ecobee(hass, data, None, add_devices_callback)

    _CONFIGURING['ecobee'] = configurator.request_config(
        hass, "Ecobee", ecobee_configuration_callback,
        description=(
            'Please authorize this app at https://www.ecobee.com/consumer'
            'portal/index.html with pin code: ' + data.ecobee.pin),
        description_image="/static/images/config_ecobee_thermostat.png",
        submit_caption="I have authorized the app."
    )


# pylint: disable=too-few-public-methods
class EcobeeData(object):
    """ Gets the latest data and update the states. """

    def __init__(self, config_filename):
        from pyecobee import Ecobee
        self.ecobee = Ecobee(config_filename)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """ Get the latest data from pyecobee. """
        self.ecobee.update()


class Thermostat(ThermostatDevice):
    """ Thermostat class for Ecobee """

    def __init__(self, data, thermostat_index):
        self.data = data
        self.thermostat_index = thermostat_index
        self.thermostat = self.data.ecobee.get_thermostat(
            self.thermostat_index)
        self._name = self.thermostat['name']
        self._away = 'away' in self.thermostat['program']['currentClimateRef']

    def update(self):
        self.data.update()
        self.thermostat = self.data.ecobee.get_thermostat(
            self.thermostat_index)
        _LOGGER.info("ecobee data updated successfully.")

    @property
    def name(self):
        """ Returns the name of the Ecobee Thermostat. """
        return self.thermostat['name']

    @property
    def unit_of_measurement(self):
        """ Unit of measurement this thermostat expresses itself in. """
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        return self.thermostat['runtime']['actualTemperature'] / 10

    @property
    def target_temperature(self):
        """ Returns the temperature we try to reach. """
        return (self.target_temperature_low + self.target_temperature_high) / 2

    @property
    def target_temperature_low(self):
        """ Returns the lower bound temperature we try to reach. """
        return int(self.thermostat['runtime']['desiredHeat'] / 10)

    @property
    def target_temperature_high(self):
        """ Returns the upper bound temperature we try to reach. """
        return int(self.thermostat['runtime']['desiredCool'] / 10)

    @property
    def humidity(self):
        """ Returns the current humidity. """
        return self.thermostat['runtime']['actualHumidity']

    @property
    def desired_fan_mode(self):
        """ Returns the desired fan mode of operation. """
        return self.thermostat['runtime']['desiredFanMode']

    @property
    def fan(self):
        """ Returns the current fan state. """
        if 'fan' in self.thermostat['equipmentStatus']:
            return STATE_ON
        else:
            return STATE_OFF

    @property
    def operation(self):
        """ Returns current operation ie. heat, cool, idle """
        status = self.thermostat['equipmentStatus']
        if status == '':
            return STATE_IDLE
        elif 'Cool' in status:
            return STATE_COOL
        elif 'auxHeat' in status:
            return STATE_HEAT
        elif 'heatPump' in status:
            return STATE_HEAT
        else:
            return status

    @property
    def mode(self):
        """ Returns current mode ie. home, away, sleep """
        mode = self.thermostat['program']['currentClimateRef']
        self._away = 'away' in mode
        return mode

    @property
    def hvac_mode(self):
        """ Return current hvac mode ie. auto, auxHeatOnly, cool, heat, off """
        return self.thermostat['settings']['hvacMode']

    @property
    def device_state_attributes(self):
        """ Returns device specific state attributes. """
        # Move these to Thermostat Device and make them global
        return {
            "humidity": self.humidity,
            "fan": self.fan,
            "mode": self.mode,
            "hvac_mode": self.hvac_mode
        }

    @property
    def is_away_mode_on(self):
        """ Returns if away mode is on. """
        return self._away

    def turn_away_mode_on(self):
        """ Turns away on. """
        self._away = True
        self.data.ecobee.set_climate_hold("away")

    def turn_away_mode_off(self):
        """ Turns away off. """
        self._away = False
        self.data.ecobee.resume_program()

    def set_temperature(self, temperature):
        """ Set new target temperature """
        temperature = int(temperature)
        low_temp = temperature - 1
        high_temp = temperature + 1
        self.data.ecobee.set_hold_temp(low_temp, high_temp)

    def set_hvac_mode(self, mode):
        """ Set HVAC mode (auto, auxHeatOnly, cool, heat, off) """
        self.data.ecobee.set_hvac_mode(mode)

    # Home and Sleep mode aren't used in UI yet:

    # def turn_home_mode_on(self):
    #     """ Turns home mode on. """
    #     self._away = False
    #     self.data.ecobee.set_climate_hold("home")

    # def turn_home_mode_off(self):
    #     """ Turns home mode off. """
    #     self._away = False
    #     self.data.ecobee.resume_program()

    # def turn_sleep_mode_on(self):
    #     """ Turns sleep mode on. """
    #     self._away = False
    #     self.data.ecobee.set_climate_hold("sleep")

    # def turn_sleep_mode_off(self):
    #     """ Turns sleep mode off. """
    #     self._away = False
    #     self.data.ecobee.resume_program()
