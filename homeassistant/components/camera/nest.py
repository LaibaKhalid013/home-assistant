"""
Support for Nest Cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.nest/
"""
import logging
from datetime import timedelta

import requests
import voluptuous as vol

import homeassistant.components.nest as nest
import homeassistant.helpers.config_validation as cv
from homeassistant.components.camera import (PLATFORM_SCHEMA, Camera, DOMAIN)
from homeassistant.const import SERVICE_TURN_ON, SERVICE_TURN_OFF, \
    ATTR_ENTITY_ID
from homeassistant.helpers.service import extract_entity_ids
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['nest']

NEST_BRAND = 'Nest'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

CAMERA_TURN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids
})

CAMERA_TURN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a Nest Cam."""
    if discovery_info is None:
        return

    camera_devices = hass.data[nest.DATA_NEST].cameras()
    cameras = [NestCamera(structure, device)
               for structure, device in camera_devices]
    add_devices(cameras, True)

    def service_handler(service):
        """Handle service call."""
        entity_ids = extract_entity_ids(hass, service)
        entities = [entity for entity in cameras
                    if entity.available and entity.entity_id in entity_ids]
        for camera in entities:
            if service.service == SERVICE_TURN_ON:
                camera.is_recording = True
            elif service.service == SERVICE_TURN_OFF:
                camera.is_recording = False

    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ON, service_handler,
        schema=CAMERA_TURN_ON_SCHEMA)

    hass.services.async_register(
        DOMAIN, SERVICE_TURN_OFF, service_handler,
        schema=CAMERA_TURN_OFF_SCHEMA)


class NestCamera(Camera):
    """Representation of a Nest Camera."""

    def __init__(self, structure, device):
        """Initialize a Nest Camera."""
        super(NestCamera, self).__init__()
        self.structure = structure
        self.device = device
        self._location = None
        self._name = None
        self._online = None
        self._is_streaming = None
        self._is_video_history_enabled = False
        # Default to non-NestAware subscribed, but will be fixed during update
        self._time_between_snapshots = timedelta(seconds=30)
        self._last_image = None
        self._next_snapshot_at = None

    @property
    def name(self):
        """Return the name of the nest, if any."""
        return self._name

    @property
    def should_poll(self):
        """Nest camera should poll periodically."""
        return True

    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return self._is_streaming

    @is_recording.setter
    def is_recording(self, is_recording):
        """Turn on/off camera streaming."""
        _LOGGER.debug("turning %s %s streaming",
                      ("off", "on")[is_recording], self.device)
        self.device.is_streaming = is_recording

    @property
    def brand(self):
        """Return the brand of the camera."""
        return NEST_BRAND

    # This doesn't seem to be getting called regularly, for some reason
    def update(self):
        """Cache value from Python-nest."""
        self._location = self.device.where
        self._name = self.device.name
        self._online = self.device.online
        self._is_streaming = self.device.is_streaming
        self._is_video_history_enabled = self.device.is_video_history_enabled

        if self._is_video_history_enabled:
            # NestAware allowed 10/min
            self._time_between_snapshots = timedelta(seconds=6)
        else:
            # Otherwise, 2/min
            self._time_between_snapshots = timedelta(seconds=30)

    def _ready_for_snapshot(self, now):
        return (self._next_snapshot_at is None or
                now > self._next_snapshot_at)

    def camera_image(self):
        """Return a still image response from the camera."""
        now = utcnow()
        if self._ready_for_snapshot(now):
            url = self.device.snapshot_url

            try:
                response = requests.get(url)
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Error getting camera image: %s", error)
                return None

            self._next_snapshot_at = now + self._time_between_snapshots
            self._last_image = response.content

        return self._last_image
