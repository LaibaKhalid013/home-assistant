"""Entity representing NASweb output."""
from __future__ import annotations

import logging
import time
from typing import Any

from webio_api import Output as NASwebOutput

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import EntityRegistry, async_get
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, OUTPUT_TRANSLATION_KEY, STATUS_UPDATE_MAX_TIME_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RelaySwitch(SwitchEntity):
    """Entity representing NASweb Output."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, nasweb_output: NASwebOutput
    ) -> None:
        """Initialize RelaySwitch."""
        self.coordinator = coordinator
        self._output = nasweb_output
        self._attr_is_on = self._output.state
        self._attr_available = True  # self._output.available
        self._attr_icon = "mdi:export"
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_translation_key = OUTPUT_TRANSLATION_KEY
        self._attr_unique_id = (
            f"{DOMAIN}.{self._output.webio_serial}.relay_switch.{self._output.index}"
        )

    async def async_added_to_hass(self) -> None:
        """Add coordinator update listener when entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update, None)
        )
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        old_available = self.available
        self._attr_is_on = self._output.state
        if (
            time.time() - self._output.last_update >= STATUS_UPDATE_MAX_TIME_INTERVAL
            or not self.coordinator.last_update_success
        ):
            self._attr_available = False
        else:
            self._attr_available = (
                self._output.available if self._output.available is not None else False
            )
        if old_available and self._output.available is None and self.unique_id:
            _LOGGER.warning("Removing entity: %s", self)
            er: EntityRegistry = async_get(self.hass)
            er.async_remove(self.entity_id)
            return
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return DeviceInfo linking this RelaySwitch with NASweb device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._output.webio_serial)},
        )

    @property
    def name(self) -> str:
        """Return name of RelaySwitch."""
        translated_name = super().name
        return f"{translated_name} {self._output.index:2d}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn On RelaySwitch."""
        await self._output.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn Off RelaySwitch."""
        await self._output.turn_off()
