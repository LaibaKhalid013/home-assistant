"""Camera entity for PrusaLink."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, JobUpdateCoordinator, PrusaLinkEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PrusaLink camera."""
    coordinator: JobUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["job"]
    async_add_entities([PrusaLinkJobPreviewEntity(coordinator)])


class PrusaLinkJobPreviewEntity(PrusaLinkEntity, Camera):
    """Defines a PrusaLink camera."""

    last_path = ""
    last_image: bytes
    _attr_translation_key = "job_preview"

    def __init__(self, coordinator: JobUpdateCoordinator) -> None:
        """Initialize a PrusaLink camera entity."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}_job_preview"

    @property
    def available(self) -> bool:
        """Get if camera is available."""
        return (
            super().available
            and (job_id := self.coordinator.data.get("id"))
            and (job_id != self.coordinator.job_id_without_thumbnail)
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the camera."""
        if not self.available:
            return None

        path = self.coordinator.data["file"]["refs"]["thumbnail"]

        if self.last_path == path:
            return self.last_image

        self.last_image = await self.coordinator.api.get_file(path)
        self.last_path = path

        return self.last_image
