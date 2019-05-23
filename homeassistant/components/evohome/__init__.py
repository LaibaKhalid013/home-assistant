"""Support for (EMEA/EU-based) Honeywell evohome systems.

Glossary:
TCS - temperature control system (a.k.a. Controller, Parent), which can have up
to 13 Children:
- 0-12 Heating zones (a.k.a. Zone), Climate devices, and
- 0-1 DHW controller, (a.k.a. Boiler), a WaterHeater device
"""
from datetime import datetime, timedelta
import logging
from typing import Any, Awaitable, Dict, Optional, List

import requests.exceptions
import voluptuous as vol

import evohomeclient2

from homeassistant.components.climate.const import (
    ATTR_AUX_HEAT, ATTR_CURRENT_HUMIDITY, ATTR_CURRENT_HVAC,
    ATTR_CURRENT_TEMPERATURE, ATTR_FAN_LIST, ATTR_FAN_MODE, ATTR_HUMIDITY,
    ATTR_HVAC_MODE, ATTR_HVAC_MODES, ATTR_MAX_HUMIDITY, ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY, ATTR_MIN_TEMP, ATTR_PRESET_LIST, ATTR_PRESET_MODE,
    ATTR_SWING_LIST, ATTR_SWING_MODE, ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_STEP, DOMAIN, HVAC_MODES,
    SERVICE_SET_AUX_HEAT, SERVICE_SET_FAN_MODE, SERVICE_SET_PRESET_MODE,
    SERVICE_SET_HUMIDITY, SERVICE_SET_HVAC_MODE, SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE, SUPPORT_AUX_HEAT, SUPPORT_CURRENT_HVAC,
    SUPPORT_FAN_MODE, SUPPORT_PRESET_MODE, SUPPORT_SWING_MODE,
    SUPPORT_TARGET_HUMIDITY, SUPPORT_TARGET_HUMIDITY_RANGE,
    SUPPORT_TARGET_TEMPERATURE_RANGE)
from homeassistant.helpers.temperature import display_temp as show_temp
from homeassistant.util.temperature import convert as convert_temperature


from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_TEMPERATURE, PRECISION_TENTHS, PRECISION_WHOLE,
    STATE_ON, STATE_OFF,

    CONF_SCAN_INTERVAL, CONF_USERNAME, CONF_PASSWORD,
    EVENT_HOMEASSISTANT_START,
    HTTP_SERVICE_UNAVAILABLE, HTTP_TOO_MANY_REQUESTS,
    PRECISION_HALVES, TEMP_CELSIUS)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, async_dispatcher_send)
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN, DATA_EVOHOME, STORAGE_VERSION, STORAGE_KEY, GWS, TCS)

_LOGGER = logging.getLogger(__name__)

CONF_LOCATION_IDX = 'location_idx'
SCAN_INTERVAL_DEFAULT = timedelta(seconds=300)
SCAN_INTERVAL_MINIMUM = timedelta(seconds=180)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_LOCATION_IDX, default=0): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL_DEFAULT):
            vol.All(cv.time_period, vol.Range(min=SCAN_INTERVAL_MINIMUM)),
    }),
}, extra=vol.ALLOW_EXTRA)

CONF_SECRETS = [
    CONF_PASSWORD,
]  # CONF_USERNAME,  # TODO: fixme

REFRESH_TOKEN = 'refresh_token'
ACCESS_TOKEN = 'access_token'
ACCESS_TOKEN_EXPIRES = 'access_token_expires'


async def async_setup(hass, hass_config):
    """Create a (EMEA/EU-based) Honeywell evohome system."""
    evo_data = hass.data[DATA_EVOHOME] = {}
    evo_data['timers'] = {}

    # use a copy, since scan_interval is rounded up to nearest 60s
    evo_data['params'] = dict(hass_config[DOMAIN])
    scan_interval = evo_data['params'][CONF_SCAN_INTERVAL]
    scan_interval = timedelta(
        minutes=(scan_interval.total_seconds() + 59) // 60)
    scan_interval = timedelta(seconds=30)                                        # TODO: for testing only

    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    app_storage = await store.async_load()
    access_token_expires = app_storage.get(ACCESS_TOKEN_EXPIRES)

    if access_token_expires:
        access_token_expires = datetime.strptime(
            access_token_expires, '%Y-%m-%d %H:%M:%S')

    _LOGGER.warn("refresh_token %s", app_storage.get(REFRESH_TOKEN))             # TODO: for testing only
    _LOGGER.warn("access_token %s", app_storage.get(ACCESS_TOKEN))               # TODO: for testing only
    _LOGGER.warn("access_token_expires %s", access_token_expires)                # TODO: for testing only

    try:
        client = evo_data['client'] = await hass.async_add_executor_job(
            evohomeclient2.EvohomeClient,
            evo_data['params'][CONF_USERNAME],
            evo_data['params'][CONF_PASSWORD],
            False,
            app_storage.get(REFRESH_TOKEN),
            app_storage.get(ACCESS_TOKEN),
            access_token_expires
        )                                                                        # TODO: partial() from functools

    except evohomeclient2.AuthenticationError as err:
        _LOGGER.error(
            "Failed to authenticate with the vendor's server. "
            "Check your username and password are correct. "
            "Resolve any errors and restart HA. Message is: %s",
            err
        )
        return False

    except requests.exceptions.ConnectionError:
        _LOGGER.error(
            "Unable to connect with the vendor's server. "
            "Check your network and the vendor's status page. "
            "Resolve any errors and restart HA."
        )
        return False

    finally:  # Redact any config data that's no longer needed
        for parameter in CONF_SECRETS:
            evo_data['params'][parameter] = 'REDACTED' \
                if evo_data['params'][parameter] else None

    _LOGGER.warn("refresh_token %s", client.refresh_token)                       # TODO: for testing only
    _LOGGER.warn("access_token %s", client.access_token)                         # TODO: for testing only
    _LOGGER.warn("access_token_expires %s",
                 client.access_token_expires.strftime('%Y-%m-%d %H:%M:%S'))      # TODO: for testing only

    app_storage[REFRESH_TOKEN] = client.refresh_token
    app_storage[ACCESS_TOKEN] = client.access_token
    app_storage[ACCESS_TOKEN_EXPIRES] = client.access_token_expires.strftime(
        '%Y-%m-%d %H:%M:%S')
    await store.async_save(app_storage)

    evo_data['status'] = {}

    # Redact any installation data that's no longer needed
    for loc in client.installation_info:
        loc['locationInfo']['locationId'] = 'REDACTED'
        loc['locationInfo']['locationOwner'] = 'REDACTED'
        loc['locationInfo']['streetAddress'] = 'REDACTED'
        loc['locationInfo']['city'] = 'REDACTED'
        loc[GWS][0]['gatewayInfo'] = 'REDACTED'

    # Pull down the installation configuration
    loc_idx = evo_data['params'][CONF_LOCATION_IDX]
    try:
        evo_data['config'] = client.installation_info[loc_idx]

    except IndexError:
        _LOGGER.error(
            "Config error: '%s' = %s, but its valid range is 0-%s. "
            "Unable to continue. Fix any configuration errors and restart HA.",
            CONF_LOCATION_IDX, loc_idx, len(client.installation_info) - 1
        )
        return False

    if _LOGGER.isEnabledFor(logging.DEBUG):
        tmp_loc = dict(evo_data['config'])
        tmp_loc['locationInfo']['postcode'] = 'REDACTED'

        _LOGGER.debug("evo_data['config']=%s", tmp_loc)

    load_platform(hass, 'climate', DOMAIN, {}, hass_config)

    if 'dhw' in evo_data['config'][GWS][0][TCS][0]:
        load_platform(hass, 'water_heater', DOMAIN, {}, hass_config)

    @callback
    def _first_update(event):
        """When HA has started, the hub knows to retrieve it's first update."""
        async_dispatcher_send(hass, DOMAIN, {'signal': 'first_update'})
        _LOGGER.debug("_first_update(): fired")                                  # TODO: remove me

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _first_update)

    return True


class EvoDevice(Entity):
    """Base for any Honeywell evohome device.

    Such devices include the Controller, (up to 12) Heating Zones and
    (optionally) a DHW controller.
    """

    def __init__(self, evo_data, client, evo_device_ref):
        """Initialize the evohome entity."""
        self._client = client
        self._evo_ref = evo_device_ref

        self._id = None
        self._name = None
        self._icon = None

        self._supported_features = None
        self._operation_list = None

        self._params = evo_data['params']
        self._timers = evo_data['timers']
        self._status = {}

        self._available = False  # should become True after first update()

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        async_dispatcher_connect(self.hass, DOMAIN, self._refresh)

    @callback
    def _refresh(self, packet):
        if packet['signal'] == 'refresh':
            self.async_schedule_update_ha_state(force_refresh=True)

    def _handle_exception(self, err):
        try:
            raise err

        except evohomeclient2.AuthenticationError:
            _LOGGER.error(
                "Failed to (re)authenticate with the vendor's server. "
                "This may be a temporary error. Message is: %s",
                err
            )

        except requests.exceptions.ConnectionError:
            # this appears to be common with Honeywell's servers
            _LOGGER.warning(
                "Unable to connect with the vendor's server. "
                "Check your network and the vendor's status page."
            )

        except requests.exceptions.HTTPError:
            if err.response.status_code == HTTP_SERVICE_UNAVAILABLE:
                _LOGGER.warning(
                    "Vendor says their server is currently unavailable. "
                    "This may be temporary; check the vendor's status page."
                )

            elif err.response.status_code == HTTP_TOO_MANY_REQUESTS:
                _LOGGER.warning(
                    "The vendor's API rate limit has been exceeded. "
                    "So will cease polling, and will resume after %s seconds.",
                    (self._params[CONF_SCAN_INTERVAL] * 3).total_seconds()
                )
                self._timers['statusUpdated'] = datetime.now() + \
                    self._params[CONF_SCAN_INTERVAL] * 3

            else:
                raise  # we don't expect/handle any other HTTPErrors

    @property
    def name(self) -> str:
        """Return the name to use in the frontend UI."""
        return self._name

    @property  # Entity
    def device_state_attributes(self):
        """Return the Evohome-specific state attributes."""
        return {'status': self._status}

    @property  # Entity
    def icon(self) -> str:
        """Return the icon to use in the frontend UI."""
        return self._icon

    @property
    def should_poll(self) -> bool:
        """Only the Controller should be polled."""
        return False

    @property
    def available(self) -> bool:
        """Return True if the device is currently available."""
        return self._available

    @property  # Entity
    def supported_features(self) -> int:
        """Get the flag of supported features of the device."""
        _LOGGER.warn("supported_features(%s) = %s", self._id, self._supported_features)
        return 2**16-1  # self._supported_features  # 2**16-1

    async def async_added_to_hass(self) -> None:  # Entity
        """Run when entity about to be added to hass."""
        async_dispatcher_connect(self.hass, DOMAIN, self._refresh)


# These properties, methods are from the ClimateDevice class
    @property  # ClimateDevice
    def precision(self) -> float:
        """Return the temperature precision to use in the frontend UI."""
        return PRECISION_HALVES

    @property  # ClimateDevice
    def temperature_unit(self) -> str:
        """Return the temperature unit to use in the frontend UI."""
        return TEMP_CELSIUS

    @property
    def operation_list(self):
        """Return the list of available operations."""
        return self._operation_list
