"""
Demo platform for the cover component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/demo/
"""
import logging
from homeassistant.components.cover import CoverDevice
from homeassistant.const import EVENT_TIME_CHANGED
from homeassistant.helpers.event import track_utc_time_change


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Demo covers."""
    add_devices([
        DemoCover(hass, 'Kitchen Window', 0),
        DemoCover(hass, 'Living Room Window', 70, 50),
    ])

_LOGGER = logging.getLogger(__name__)


class DemoCover(CoverDevice):
    """Representation of a demo cover."""

    # pylint: disable=no-self-use, too-many-instance-attributes
    def __init__(self, hass, name, position, tilt_position=None):
        """Initialize the cover."""
        self.hass = hass
        self._name = name
        self._position = position
        self._set_position = None
        self._set_tilt_position = None
        self._tilt_position = tilt_position
        self._closing = True
        self._closing_tilt = True
        self._listener_cover = None
        self._listener_cover_tilt = None

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed for a demo cover."""
        return False

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position of the cover."""
        return self._tilt_position

    def close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.info("closing cover, self._position=%s", self._position)
        if self._position == 0:
            _LOGGER.info("self._position=0")
            return

        self._listen_cover()
        self._closing = True

    def close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        if self._tilt_position == 0:
            return

        self._listen_cover_tilt()
        self._closing_tilt = True

    def open_cover(self, **kwargs):
        """Open the cover."""
        if self._position == 100:
            return

        self._listen_cover()
        self._closing = False

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        if self._tilt_position == 100:
            return

        self._listen_cover_tilt()
        self._closing_tilt = False

    def set_cover_position(self, position, **kwargs):
        """Move the cover to a specific position."""
        self._set_position = round(position, -1)
        if self._position == position:
            return
        self._listen_cover()
        self._closing = position < self._position

    def set_cover_tilt_position(self, tilt_position, **kwargs):
        """Move the cover til to a specific position."""
        self._set_tilt_position = round(tilt_position, -1)
        if self._tilt_position == tilt_position:
            return
        self._listen_cover_tilt()
        self._closing_tilt = tilt_position < self._tilt_position

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        if self._listener_cover is not None:
            self.hass.bus.remove_listener(EVENT_TIME_CHANGED,
                                          self._listener_cover)
            self._listener_cover = None
            self._set_position = None

    def stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt."""
        if self._listener_cover_tilt is not None:
            self.hass.bus.remove_listener(EVENT_TIME_CHANGED,
                                          self._listener_cover_tilt)
            self._listener_cover_tilt = None
            self._set_tilt_position = None

    def _listen_cover(self):
        """Listen for changes in cover."""
        _LOGGER.info("_listener_cover called")
        if self._listener_cover is None:
            _LOGGER.info("self._listener_cover is None")
            self._listener_cover = track_utc_time_change(
                self.hass, self._time_changed_cover)

    def _time_changed_cover(self, now):
        """Track time changes."""
        _LOGGER.info("_time_changed_cover fired now=%s", now)
        if self._closing:
            self._position -= 10
        else:
            self._position += 10

        if self._position in (100, 0, self._set_position):
            self.stop_cover()
        _LOGGER.info("updating ha state")
        self.update_ha_state()

    def _listen_cover_tilt(self):
        """Listen for changes in cover tilt."""
        if self._listener_cover_tilt is None:
            self._listener_cover_tilt = track_utc_time_change(
                self.hass, self._time_changed_cover_tilt)

    def _time_changed_cover_tilt(self, now):
        """Track time changes."""
        if self._closing_tilt:
            self._tilt_position -= 10
        else:
            self._tilt_position += 10

        if self._tilt_position in (100, 0, self._set_tilt_position):
            self.stop_cover_tilt()

        self.update_ha_state()
