"""DataUpdateCoordinator for LaCrosse View."""
from __future__ import annotations

from datetime import datetime, timedelta

from lacrosse_view import HTTPError, LaCrosse, Location, LoginError, Sensor

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import LOGGER, SCAN_INTERVAL


class LaCrosseUpdateCoordinator(DataUpdateCoordinator[list[Sensor]]):
    """DataUpdateCoordinator for LaCrosse View."""

    username: str
    password: str
    name: str
    id: str
    hass: HomeAssistant
    is_metric: bool

    def __init__(
        self,
        hass: HomeAssistant,
        api: LaCrosse,
        entry: ConfigEntry,
    ) -> None:
        """Initialize DataUpdateCoordinator for LaCrosse View."""
        self.api = api
        self.last_update = datetime.utcnow()
        self.username = entry.data["username"]
        self.password = entry.data["password"]
        self.hass = hass
        self.name = entry.data["name"]
        self.id = entry.data["id"]
        self.is_metric = hass.config.units.is_metric
        super().__init__(
            hass,
            LOGGER,
            name="LaCrosse View",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> list[Sensor]:
        """Get the data for LaCrosse View."""
        now = datetime.utcnow()

        if self.last_update < now - timedelta(minutes=59):  # Get new token
            self.last_update = now
            try:
                await self.api.login(self.username, self.password)
            except LoginError as error:
                raise ConfigEntryAuthFailed from error

        # Get the timestamp for yesterday at 6 PM (this is what is used in the app, i noticed it when proxying the request)
        yesterday = now - timedelta(days=1)
        yesterday = yesterday.replace(hour=18, minute=0, second=0, microsecond=0)
        yesterday_timestamp = datetime.timestamp(yesterday)

        try:
            sensors = await self.api.get_sensors(
                location=Location(id=self.id, name=self.name),
                tz=self.hass.config.time_zone,
                start=str(int(yesterday_timestamp)),
                end=str(int(datetime.timestamp(now))),
            )
        except HTTPError as error:
            raise ConfigEntryNotReady from error

        # Verify that we have permission to read the sensors
        for sensor in sensors:
            if not sensor.permissions.get("read", False):
                raise ConfigEntryAuthFailed(
                    f"This account does not have permission to read {sensor.name}"
                )

        return sensors
