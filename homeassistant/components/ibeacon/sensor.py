"""Support for iBeacon device sensors."""
from __future__ import annotations

from ibeacon_ble import iBeaconAdvertisement

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LENGTH_METERS, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_IBEACON_DEVICE_NEW
from .coordinator import IBeaconCoordinator
from .entity import IBeaconEntity

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="rssi",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="power",
        name="Power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="distance",
        name="Distance",
        native_unit_of_measurement=LENGTH_METERS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up device tracker for iBeacon Tracker component."""
    coordinator: IBeaconCoordinator = hass.data[DOMAIN]

    @callback
    def _async_device_new(
        unique_id: str,
        name: str,
        parsed: iBeaconAdvertisement,
    ) -> None:
        """Signal a new device."""
        async_add_entities(
            IBeaconSensorEntity(
                coordinator,
                description,
                name,
                unique_id,
                parsed,
            )
            for description in SENSOR_DESCRIPTIONS
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_IBEACON_DEVICE_NEW, _async_device_new)
    )


class IBeaconSensorEntity(IBeaconEntity, SensorEntity):
    """An iBeacon sensor entity."""

    def __init__(
        self,
        coordinator: IBeaconCoordinator,
        description: SensorEntityDescription,
        name: str,
        unique_id: str,
        parsed: iBeaconAdvertisement,
    ) -> None:
        """Initialize an iBeacon sensor entity."""
        super().__init__(coordinator, name, unique_id, parsed)
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description

    @callback
    def _async_seen(
        self,
        parsed: iBeaconAdvertisement,
    ) -> None:
        """Update state."""
        self._attr_available = True
        self._parsed = parsed
        self.async_write_ha_state()

    @callback
    def _async_unavailable(self) -> None:
        """Update state."""
        self._attr_available = False
        self.async_write_ha_state()
