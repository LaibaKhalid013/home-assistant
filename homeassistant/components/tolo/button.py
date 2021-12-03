"""TOLO Sauna Button controls."""

from tololib.const import LampMode

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENTITY_CATEGORY_CONFIG
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ToloSaunaCoordinatorEntity, ToloSaunaUpdateCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons for TOLO Sauna."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ToloLampNextColorButton(coordinator, entry),
        ]
    )


class ToloLampNextColorButton(ToloSaunaCoordinatorEntity, ButtonEntity):
    """Button for switching to the next lamp color."""

    _attr_entity_category = ENTITY_CATEGORY_CONFIG
    _attr_icon = "mdi:palette"
    _attr_name = "Next Color"

    def __init__(
        self, coordinator: ToloSaunaUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize lamp next color button entity."""
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_lamp_next_color"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.data.status.lamp_on
            and self.coordinator.data.settings.lamp_mode == LampMode.MANUAL
        )

    def press(self) -> None:
        """Execute action when lamp change color button was pressed."""
        self.coordinator.client.lamp_change_color()
