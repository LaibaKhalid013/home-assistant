"""Base classes for Hydrawise entities."""

from __future__ import annotations

from pydrawise.schema import Controller, Sensor, Zone

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HydrawiseDataUpdateCoordinator


class HydrawiseEntity(CoordinatorEntity[HydrawiseDataUpdateCoordinator]):
    """Entity class for Hydrawise devices."""

    _attr_attribution = "Data provided by hydrawise.com"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HydrawiseDataUpdateCoordinator,
        description: EntityDescription,
        controller: Controller,
        *,
        zone: Zone | None = None,
        sensor: Sensor | None = None,
    ) -> None:
        """Initialize the Hydrawise entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self.controller = controller
        self.zone_id = zone.id if zone else None
        self.sensor_id = sensor.id if sensor else None
        self._device_id = str(zone.id) if zone is not None else str(controller.id)
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=zone.name if zone is not None else controller.name,
            model="Zone" if zone is not None else controller.hardware.model.description,
            manufacturer=MANUFACTURER,
        )
        if zone is not None or sensor is not None:
            self._attr_device_info["via_device"] = (DOMAIN, str(controller.id))
        self._update_attrs()

    @property
    def zone(self) -> Zone | None:
        """Return the entity zone."""
        return self.coordinator.data.zones[self.zone_id] if self.zone_id else None

    @property
    def sensor(self) -> Sensor | None:
        """Return the entity sensor."""
        return self.coordinator.data.sensors[self.sensor_id] if self.sensor_id else None

    def _update_attrs(self) -> None:
        """Update state attributes."""
        return  # pragma: no cover

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get the latest data and updates the state."""
        self.controller = self.coordinator.data.controllers[self.controller.id]
        self._update_attrs()
        super()._handle_coordinator_update()
