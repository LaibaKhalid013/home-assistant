"""Support for Tractive device trackers."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import Trackables
from .const import (
    CLIENT,
    DOMAIN,
    SERVER_UNAVAILABLE,
    TRACKABLES,
    TRACKER_HARDWARE_STATUS_UPDATED,
    TRACKER_POSITION_UPDATED,
)
from .entity import TractiveEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tractive device trackers."""
    client = hass.data[DOMAIN][entry.entry_id][CLIENT]
    trackables = hass.data[DOMAIN][entry.entry_id][TRACKABLES]

    entities = [TractiveDeviceTracker(client.user_id, item) for item in trackables]

    async_add_entities(entities)


class TractiveDeviceTracker(TractiveEntity, TrackerEntity):
    """Tractive device tracker."""

    _attr_icon = "mdi:paw"

    def __init__(self, user_id: str, item: Trackables) -> None:
        """Initialize tracker entity."""
        super().__init__(user_id, item.trackable, item.tracker_details)

        self._battery_level = item.hw_info["battery_level"]
        self._latitude = item.pos_report["latlong"][0]
        self._longitude = item.pos_report["latlong"][1]
        self._accuracy = item.pos_report["pos_uncertainty"]

        self._attr_name = f"{self._tracker_id} {item.trackable['details']['name']}"
        self._attr_unique_id = item.trackable["_id"]

    @property
    def source_type(self) -> str:
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def location_accuracy(self) -> int:
        """Return the gps accuracy of the device."""
        return self._accuracy

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        return self._battery_level

    @callback
    def _handle_hardware_status_update(self, event: dict[str, Any]) -> None:
        self._battery_level = event["battery_level"]
        self._attr_available = True
        self.async_write_ha_state()

    @callback
    def _handle_position_update(self, event: dict[str, Any]) -> None:
        self._latitude = event["latitude"]
        self._longitude = event["longitude"]
        self._accuracy = event["accuracy"]
        self._attr_available = True
        self.async_write_ha_state()

    @callback
    def _handle_server_unavailable(self) -> None:
        self._latitude = None
        self._longitude = None
        self._accuracy = None
        self._battery_level = None
        self._attr_available = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{TRACKER_HARDWARE_STATUS_UPDATED}-{self._tracker_id}",
                self._handle_hardware_status_update,
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{TRACKER_POSITION_UPDATED}-{self._tracker_id}",
                self._handle_position_update,
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SERVER_UNAVAILABLE}-{self._user_id}",
                self._handle_server_unavailable,
            )
        )
