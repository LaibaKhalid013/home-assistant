"""Base Entity for JustNimbus sensors."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JustNimbusCoordinator


class JustNimbusEntity(
    CoordinatorEntity[JustNimbusCoordinator],
    Entity,
):
    """Defines a base JustNimbus entity."""

    def __init__(
        self,
        *,
        device_id: str,
        coordinator: JustNimbusCoordinator,
    ) -> None:
        """Initialize the JustNimbus entity."""
        super().__init__(coordinator=coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name="JustNimbus Sensor",
            manufacturer="JustNimbus",
        )

    @property
    def available(self) -> bool:
        """Return device availability."""
        return super().available and getattr(self.coordinator.data, "error_code") == 0
