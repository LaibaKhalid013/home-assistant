"""Binary sensor platform for integration_blueprint."""
import logging
from typing import Any

from pydeako.deako import Deako

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODEL_DIMMER, MODEL_SMART

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Configure the platform."""
    client: Deako = hass.data[DOMAIN][config.entry_id]

    devices = client.get_devices()
    if len(devices) == 0:
        # If deako devices are advertising on mdns, we should be able to get at least one device
        _LOGGER.warning("No devices found from local integration")
        await client.disconnect()
        return
    lights = [DeakoLightEntity(client, uuid) for uuid in devices]
    add_entities(lights)


class DeakoLightEntity(LightEntity):
    """Deako LightEntity class."""

    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(self, client: Deako, uuid: str) -> None:
        """Save connection reference."""
        self.client = client
        self._attr_unique_id = uuid
        self._attr_available = True

        # https://developers.home-assistant.io/docs/core/entity/#has_entity_name-true-mandatory-for-new-integrations
        # since light entity is the main feature of deako devices
        self._attr_name = None

        state = self.get_state()
        dimmable = state is not None and state.get("dim") is not None

        model = MODEL_SMART
        self._attr_color_mode = ColorMode.ONOFF
        if dimmable:
            model = MODEL_DIMMER
            self._attr_color_mode = ColorMode.BRIGHTNESS

        self._attr_supported_color_modes = {self._attr_color_mode}

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uuid)},
            name=client.get_name(uuid),
            manufacturer="Deako",
            model=model,
        )

        client.set_state_callback(uuid, self.on_update)
        self.update()  # set initial state

    def on_update(self) -> None:
        """State update callback."""
        self.update()
        self.schedule_update_ha_state()

    def get_state(self) -> dict | None:
        """Return state of entity from client."""
        if self._attr_unique_id is None:
            return None
        return self.client.get_state(self._attr_unique_id)

    async def control_device(self, power: bool, dim: int | None = None) -> None:
        """Control entity state via client."""
        if self._attr_unique_id is not None:
            await self.client.control_device(self._attr_unique_id, power, dim)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        dim = None
        if ATTR_BRIGHTNESS in kwargs:
            dim = round(kwargs[ATTR_BRIGHTNESS] / 2.55, 0)
        await self.control_device(True, dim)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        await self.control_device(False)

    def update(self) -> None:
        """Call to update state."""
        state = self.get_state()
        if state is not None:
            self._attr_is_on = bool(state.get("power", False))
            if (
                self._attr_supported_color_modes is not None
                and ColorMode.BRIGHTNESS in self._attr_supported_color_modes
            ):
                self._attr_brightness = int(round(state.get("dim", 0) * 2.55))
