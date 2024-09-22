"""Support for scenes provided by WMS WebControl pro."""

from __future__ import annotations

from typing import Any

from wmspro.scene import Scene as WMS_Scene

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WebControlProConfigEntry
from .const import ATTRIBUTION, DOMAIN, MANUFACTURER


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WebControlProConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WMS based scenes from a config entry."""
    hub = config_entry.runtime_data

    async_add_entities(
        WebControlProScene(config_entry.entry_id, scene)
        for scene in hub.scenes.values()
    )


class WebControlProScene(Scene):
    """Representation of a WMS based scene."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, config_entry_id: str, scene: WMS_Scene) -> None:
        """Initialize the entity with the configured scene."""
        super().__init__()
        scene_id_str = str(scene.id)
        self._scene = scene
        self._attr_unique_id = scene_id_str
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, scene_id_str)},
            manufacturer=MANUFACTURER,
            model="Scene",
            name=scene.name,
            serial_number=scene_id_str,
            suggested_area=scene.room.name,
            via_device=(DOMAIN, config_entry_id),
            configuration_url=f"http://{scene.host}/control",
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate scene. Try to get entities into requested state."""
        await self._scene()
