"""
Support for Tellstick switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tellstick/
"""
import voluptuous as vol

from homeassistant.components.tellstick import (DEFAULT_SIGNAL_REPETITIONS,
                                                ATTR_DISCOVER_DEVICES,
                                                ATTR_DISCOVER_CONFIG,
                                                DOMAIN, TellstickDevice)
from homeassistant.helpers.entity import ToggleEntity

PLATFORM_SCHEMA = vol.Schema({vol.Required("platform"): DOMAIN})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup Tellstick switches."""
    if (discovery_info is None or
            discovery_info[ATTR_DISCOVER_DEVICES] is None):
        return

    # Allow platform level override, fallback to module config
    signal_repetitions = discovery_info.get(ATTR_DISCOVER_CONFIG,
                                            DEFAULT_SIGNAL_REPETITIONS)

    add_devices(TellstickSwitch(tellcore_id, signal_repetitions)
                for tellcore_id in discovery_info[ATTR_DISCOVER_DEVICES])


class TellstickSwitch(TellstickDevice, ToggleEntity):
    """Representation of a Tellstick switch."""

    def _parse_ha_data(self, kwargs):
        return None

    def _parse_tellcore_data(self, tellcore_data)
        return None

    def _update_model(self, new_state, data):
        self._state = new_state

    def _send_tellstick_command(self):
        if self._state:
            self._tellcore_device.turn_on()
        else:
            self._tellcore_device.turn_off()

    @property
    def force_update(self) -> bool:
        """Will trigger anytime the state property is updated."""
        return True
