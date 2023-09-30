"""WeatherKit sensors."""

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolumetricFlux
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WeatherKitDataUpdateCoordinator
from .entity import WeatherKitEntity

SENSORS = (
    SensorEntityDescription(
        key="precipitationIntensity",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    ),
    SensorEntityDescription(
        key="pressureTrend",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:gauge",
        options=["rising", "falling", "steady"],
        translation_key="pressure_trend",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensor entities from a config_entry."""
    coordinator: WeatherKitDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    sensors = [WeatherKitSensor(coordinator, description) for description in SENSORS]

    async_add_entities(sensors)


class WeatherKitSensor(
    CoordinatorEntity[WeatherKitDataUpdateCoordinator], WeatherKitEntity, SensorEntity
):
    """WeatherKit sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WeatherKitDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        WeatherKitEntity.__init__(
            self, coordinator, unique_id_suffix=entity_description.key
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return native value from coordinator current weather."""
        return self.coordinator.data["currentWeather"][self.entity_description.key]
