"""
Support for AlarmDecoder zone states- represented as binary sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.alarmdecoder/
"""
import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.alarmdecoder import (ZONE_SCHEMA,
                                                   CONF_ZONES,
                                                   CONF_ZONE_NAME,
                                                   CONF_ZONE_TYPE,
                                                   CONF_ZONE_RFID,
                                                   SIGNAL_RFX_MESSAGE,
                                                   SIGNAL_ZONE_FAULT,
                                                   SIGNAL_ZONE_RESTORE)

DEPENDENCIES = ['alarmdecoder']

_LOGGER = logging.getLogger(__name__)

ATTR_RF_STATE = 'rfstate'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the AlarmDecoder binary sensor devices."""
    configured_zones = discovery_info[CONF_ZONES]

    devices = []
    for zone_num in configured_zones:
        device_config_data = ZONE_SCHEMA(configured_zones[zone_num])
        zone_type = device_config_data[CONF_ZONE_TYPE]
        zone_name = device_config_data[CONF_ZONE_NAME]
        zone_rfid = device_config_data[CONF_ZONE_RFID]
        device = AlarmDecoderBinarySensor(
            zone_num, zone_name, zone_type, zone_rfid)
        devices.append(device)

    add_devices(devices)

    return True


class AlarmDecoderBinarySensor(BinarySensorDevice):
    """Representation of an AlarmDecoder binary sensor."""

    def __init__(self, zone_number, zone_name, zone_type, zone_rfid):
        """Initialize the binary_sensor."""
        self._zone_number = zone_number
        self._zone_type = zone_type
        self._state = 0
        self._name = zone_name
        self._type = zone_type
        self._rfid = zone_rfid
        self._rfstate = 0

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_ZONE_FAULT, self._fault_callback)

        self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_ZONE_RESTORE, self._restore_callback)

        self.hass.helpers.dispatcher.async_dispatcher_connect(
            self.hass, SIGNAL_RFX_MESSAGE, self._rfx_message_callback)

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self):
        """Icon for device by its type."""
        if "window" in self._name.lower():
            return "mdi:window-open" if self.is_on else "mdi:window-closed"

        if self._type == 'smoke':
            return "mdi:fire"

        return None

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        if self._rfid:
            attr[ATTR_RF_STATE] = self._rfstate
        return attr

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state == 1

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self._zone_type

    def _fault_callback(self, zone):
        """Update the zone's state, if needed."""
        if zone is None or int(zone) == self._zone_number:
            self._state = 1
            self.schedule_update_ha_state()

    def _restore_callback(self, zone):
        """Update the zone's state, if needed."""
        if zone is None or int(zone) == self._zone_number:
            self._state = 0
            self.schedule_update_ha_state()

    def _rfx_message_callback(self, message):
        """Update RF state."""
        if self._rfid and message and message.serial_number == self._rfid:
            self._rfstate = message.value
            self.schedule_update_ha_state()
