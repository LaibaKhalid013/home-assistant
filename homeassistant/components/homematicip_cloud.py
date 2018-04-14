"""
Support for HomematicIP components.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/homematicip_cloud/
"""

import asyncio
import logging
import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['homematicip==0.9.1']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'homematicip_cloud'

COMPONTENTS = [
    'sensor',
    # 'binary_sensor',
    # 'climate',
    # 'switch',
    # 'light',
    # 'alarm_control_panel'
]

CONF_NAME = 'name'
CONF_ACCESSPOINT = 'accesspoint'
CONF_AUTHTOKEN = 'authtoken'

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(DOMAIN): [vol.Schema({
        vol.Optional(CONF_NAME, default=None): vol.Any(None, cv.string),
        vol.Required(CONF_ACCESSPOINT): cv.string,
        vol.Required(CONF_AUTHTOKEN): cv.string,
    })],
}, extra=vol.ALLOW_EXTRA)

HMIP_ACCESS_POINT = 'Access Point'
HMIP_HUB = 'HmIP-HUB'

ATTR_HOME_ID = 'home_id'
ATTR_HOME_NAME = 'home_name'
ATTR_DEVICE_ID = 'device_id'
ATTR_DEVICE_LABEL = 'device_label'
ATTR_STATUS_UPDATE = 'status_update'
ATTR_FIRMWARE_STATE = 'firmware_state'
ATTR_UNREACHABLE = 'unreachable'
ATTR_LOW_BATTERY = 'low_battery'
ATTR_MODEL_TYPE = 'model_type'
ATTR_GROUP_TYPE = 'group_type'
ATTR_DEVICE_RSSI = 'device_rssi'
ATTR_DUTY_CYCLE = 'duty_cycle'
ATTR_CONNECTED = 'connected'
ATTR_SABOTAGE = 'sabotage'
ATTR_OPERATION_LOCK = 'operation_lock'


class HomematicipConnector:
    """Manages HomematicIP http and websocket connection."""

    def __init__(self, config, websession, hass):
        """Initialize HomematicIP cloud connection."""
        from homematicip.async.home import AsyncHome
        self._hass = hass
        self._ws_close_requested = False
        self._retry_task = None
        self._tries = 0
        self._accesspoint = config.get(CONF_ACCESSPOINT)
        self._authtoken = config.get(CONF_AUTHTOKEN)

        self.home = AsyncHome(hass.loop, websession)
        self.home.set_auth_token(self._authtoken)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.close())

    async def init(self):
        """Initial connection."""
        await self.home.init(self._accesspoint)
        await self.home.get_current_state()

    async def _handle_connection(self):
        """Handle websocket connection."""
        from homematicip.base.base_connection import HmipConnectionError

        await self.home.get_current_state()
        hmip_events = await self.home.enable_events()
        try:
            await hmip_events
        except HmipConnectionError:
            return
        return

    async def connect(self):
        """Start websocket connection."""
        self._tries = 0
        while True:
            try:
                await self._handle_connection()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error")
            if self._ws_close_requested:
                break
            self._ws_close_requested = False
            self._tries += 1
            try:
                self._retry_task = self._hass.async_add_job(asyncio.sleep(
                    2 ** min(9, self._tries), loop=self._hass.loop))
                await self._retry_task
            except asyncio.CancelledError:
                break
            _LOGGER.info('Reconnect (%s) to the HomematicIP cloud server.',
                         self._tries)

    async def close(self):
        """Close the websocket connection."""
        self._ws_close_requested = True
        if self._retry_task is not None:
            self._retry_task.cancel()
        await self.home.disable_events()
        _LOGGER.info("Closed connection to HomematicIP cloud server.")


async def async_setup(hass, config):
    """Set up the HomematicIP component."""
    from homematicip.base.base_connection import HmipConnectionError

    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info('Loading config for HomematicIP cloud connection.')
    accesspoints = config.get(DOMAIN, [])
    for conf in accesspoints:
        _websession = async_get_clientsession(hass)
        _hmip = HomematicipConnector(conf, _websession, hass)
        try:
            await _hmip.init()
        except HmipConnectionError:
            _LOGGER.error('Failed to connect to the HomematicIP cloud server.')
            return False

        home = _hmip.home
        home.name = conf.get(CONF_NAME)
        home.label = HMIP_ACCESS_POINT
        home.modelType = HMIP_HUB

        hass.data[DOMAIN][home.id] = home
        _LOGGER.info('Connected to the HomematicIP cloud server.')
        homeid = {ATTR_HOME_ID: home.id}
        for component in COMPONTENTS:
            hass.async_add_job(async_load_platform(hass, component, DOMAIN,
                                                   homeid, config))

        hass.loop.create_task(_hmip.connect())
    return True


class HomematicipGenericDevice(Entity):
    """Representation of an HomematicIP generic device."""

    def __init__(self, home, device, post=None):
        """Initialize the generic device."""
        self._home = home
        self._device = device
        self.post = post
        _LOGGER.info('Setting up %s (%s)', self._name(),
                     self._device.modelType)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._device.on_update(self._device_changed)

    def _device_changed(self, json, **kwargs):
        """Handle device state changes."""
        _LOGGER.debug('Event %s (%s)', self._name(), self._device.modelType)
        self.async_schedule_update_ha_state()

    def _name(self):
        """Return the name of the generic device."""
        name = self._device.label
        if self._home.name is not None:
            name = self._home.name + ' ' + name
        if self.post is not None:
            name = name + ' ' + self.post
        return name

    @property
    def name(self):
        """Return the name of the generic device."""
        return self._name()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def available(self):
        """Device available."""
        return not self._device.unreach

    @property
    def device_state_attributes(self):
        """Return the state attributes of the generic device."""
        laststatus = ''
        if self._device.lastStatusUpdate is not None:
            laststatus = self._device.lastStatusUpdate.isoformat()
        return {
            ATTR_HOME_NAME: self._home.name,
            ATTR_DEVICE_LABEL: self._device.label,
            ATTR_STATUS_UPDATE: laststatus,
            ATTR_FIRMWARE_STATE: self._device.updateState.lower(),
            ATTR_UNREACHABLE: self._device.unreach,
            ATTR_LOW_BATTERY: self._device.lowBat,
            ATTR_DEVICE_RSSI: self._device.rssiDeviceValue,
            ATTR_MODEL_TYPE: self._device.modelType
        }
