"""Matter sensors."""
from __future__ import annotations

from chip.clusters import Objects as clusters
from chip.clusters.Types import Nullable, NullValue

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    Platform,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MatterEntity
from .helpers import get_matter
from .models import MatterDiscoverySchema


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Matter sensors from Config Entry."""
    matter = get_matter(hass)
    matter.register_platform_handler(Platform.SENSOR, async_add_entities)


class MatterSensor(MatterEntity, SensorEntity):
    """Representation of a Matter sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @callback
    def _update_from_device(self) -> None:
        """Update from device."""
        value: Nullable | float | None
        value = self.get_matter_attribute_value(self._entity_info.primary_attribute)
        if value in (None, NullValue):
            return None
        if value_convert := self._entity_info.measurement_to_ha:
            value = value_convert(value)
        self._attr_native_value = value


# Discovery schema(s) to map Matter Attributes to HA entities
DISCOVERY_SCHEMAS = [
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="TemperatureSensor",
            name="Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        entity_class=MatterSensor,
        required_attributes=(clusters.TemperatureMeasurement.Attributes.MeasuredValue,),
        measurement_to_ha=lambda x: x / 100,
    ),
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="PressureSensor",
            name="Pressure",
            native_unit_of_measurement=UnitOfPressure.KPA,
            device_class=SensorDeviceClass.PRESSURE,
        ),
        entity_class=MatterSensor,
        required_attributes=(clusters.PressureMeasurement.Attributes.MeasuredValue,),
        measurement_to_ha=lambda x: x / 10,
    ),
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="FlowSensor",
            name="Flow",
            native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
            device_class=SensorDeviceClass.WATER,  # what is the device class here ?
        ),
        entity_class=MatterSensor,
        required_attributes=(clusters.FlowMeasurement.Attributes.MeasuredValue,),
        measurement_to_ha=lambda x: x / 10,
    ),
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="HumiditySensor",
            name="Humidity",
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
        ),
        entity_class=MatterSensor,
        required_attributes=(
            clusters.RelativeHumidityMeasurement.Attributes.MeasuredValue,
        ),
        measurement_to_ha=lambda x: x / 100,
    ),
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="LightSensor",
            name="Illuminance",
            native_unit_of_measurement=LIGHT_LUX,
            device_class=SensorDeviceClass.ILLUMINANCE,
        ),
        entity_class=MatterSensor,
        required_attributes=(clusters.IlluminanceMeasurement.Attributes.MeasuredValue,),
        measurement_to_ha=lambda x: round(pow(10, ((x - 1) / 10000)), 1),
    ),
    MatterDiscoverySchema(
        platform=Platform.SENSOR,
        entity_description=SensorEntityDescription(
            key="PowerSource",
            name="Battery",
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
        ),
        entity_class=MatterSensor,
        required_attributes=(clusters.PowerSource.Attributes.BatPercentRemaining,),
        # value has double precision
        measurement_to_ha=lambda x: int(x / 2) if x is not None else None,
    ),
]
