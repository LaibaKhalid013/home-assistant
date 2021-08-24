"""Support for AVM FRITZ!SmartHome temperature sensor only devices."""
from __future__ import annotations

from homeassistant.components.fritzbox.model import FritzSensorEntityDescription
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FritzBoxEntity, FritzBoxSensorEntity
from .const import CONF_COORDINATOR, DOMAIN as FRITZBOX_DOMAIN, SENSOR_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the FRITZ!SmartHome sensor from ConfigEntry."""
    entities: list[FritzBoxEntity] = []
    coordinator = hass.data[FRITZBOX_DOMAIN][entry.entry_id][CONF_COORDINATOR]

    for ain, device in coordinator.data.items():
        for description in SENSOR_DESCRIPTIONS:
            if description.suitable is not None and description.suitable(device):
                entities.append(
                    FritzBoxSensor(
                        description,
                        coordinator,
                        ain,
                    )
                )
    async_add_entities(entities)


class FritzBoxSensor(FritzBoxSensorEntity, SensorEntity):
    """The entity class for FRITZ!SmartHome sensors."""

    entity_description: FritzSensorEntityDescription

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the sensor."""
        if self.entity_description.state is not None:
            return self.entity_description.state(self.device)
        return None
