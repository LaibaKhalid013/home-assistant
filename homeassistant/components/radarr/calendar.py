"""Support for Radarr calendar items."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RadarrConfigEntry
from .coordinator import CalendarUpdateCoordinator, RadarrEvent
from .entity import RadarrEntity

CALENDAR_TYPE = EntityDescription(
    key="calendar",
    name=None,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RadarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Radarr calendar entity."""
    coordinator = entry.runtime_data.calendar
    async_add_entities([RadarrCalendarEntity(coordinator, CALENDAR_TYPE)])


class RadarrCalendarEntity(RadarrEntity, CalendarEntity):
    """A Radarr calendar entity."""

    coordinator: CalendarUpdateCoordinator

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self.coordinator.event:
            return None
        return CalendarEvent(
            summary=self.coordinator.event.summary,
            start=cast(datetime, self.coordinator.event.start).date(),
            end=cast(datetime, self.coordinator.event.end).date(),
            description=self.coordinator.event.description,
        )

    # pylint: disable-next=hass-return-type
    async def async_get_events(  # type: ignore[override]
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[RadarrEvent]:
        """Get all events in a specific time frame."""
        return [
            RadarrEvent(
                summary=e.summary,
                start=cast(datetime, e.start).date(),
                end=cast(datetime, e.end).date(),
                description=e.description,
                release_type=e.release_type,
            )
            for e in await self.coordinator.async_get_events(start_date, end_date)
        ]

    @callback
    def async_write_ha_state(self) -> None:
        """Write the state to the state machine."""
        if self.coordinator.event:
            self._attr_extra_state_attributes = {
                "release_type": self.coordinator.event.release_type
            }
        else:
            self._attr_extra_state_attributes = {}
        super().async_write_ha_state()
