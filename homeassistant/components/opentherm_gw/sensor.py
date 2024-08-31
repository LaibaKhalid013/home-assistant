"""Support for OpenTherm Gateway sensors."""

from dataclasses import dataclass

import pyotgw.vars as gw_vars

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    PERCENTAGE,
    EntityCategory,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BOILER_DEVICE_DESCRIPTION,
    DATA_GATEWAYS,
    DATA_OPENTHERM_GW,
    GATEWAY_DEVICE_DESCRIPTION,
    THERMOSTAT_DEVICE_DESCRIPTION,
    OpenThermDataSource,
)
from .entity import OpenThermEntity, OpenThermEntityDescription

SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION = 1


@dataclass(frozen=True, kw_only=True)
class OpenThermSensorEntityDescription(
    SensorEntityDescription, OpenThermEntityDescription
):
    """Describes an opentherm_gw sensor entity."""

    make_state_lowercase: bool = True


SENSOR_DESCRIPTIONS: tuple[OpenThermSensorEntityDescription, ...] = (
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CONTROL_SETPOINT,
        translation_key="control_setpoint_n",
        translation_placeholders={"circuit_number": "1"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CONTROL_SETPOINT_2,
        translation_key="control_setpoint_n",
        translation_placeholders={"circuit_number": "2"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_MEMBERID,
        translation_key="manufacturer_id",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_OEM_FAULT,
        translation_key="oem_fault_code",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_COOLING_CONTROL,
        translation_key="cooling_control",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_MAX_RELATIVE_MOD,
        translation_key="max_relative_mod_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_MAX_CAPACITY,
        translation_key="max_capacity",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_MIN_MOD_LEVEL,
        translation_key="min_mod_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_REL_MOD_LEVEL,
        translation_key="relative_mod_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CH_WATER_PRESS,
        translation_key="central_heating_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_FLOW_RATE,
        translation_key="hot_water_flow_rate",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CH_WATER_TEMP,
        translation_key="central_heating_temperature_n",
        translation_placeholders={"circuit_number": "1"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CH_WATER_TEMP_2,
        translation_key="central_heating_temperature_n",
        translation_placeholders={"circuit_number": "2"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_TEMP,
        translation_key="hot_water_temperature_n",
        translation_placeholders={"circuit_number": "1"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_TEMP_2,
        translation_key="hot_water_temperature_n",
        translation_placeholders={"circuit_number": "2"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_RETURN_WATER_TEMP,
        translation_key="return_water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SOLAR_STORAGE_TEMP,
        translation_key="solar_storage_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SOLAR_COLL_TEMP,
        translation_key="solar_collector_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_EXHAUST_TEMP,
        translation_key="exhaust_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_DHW_MAX_SETP,
        translation_key="max_hot_water_setpoint_upper",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_DHW_MIN_SETP,
        translation_key="max_hot_water_setpoint_lower",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_CH_MAX_SETP,
        translation_key="max_central_heating_setpoint_upper",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_CH_MIN_SETP,
        translation_key="max_central_heating_setpoint_lower",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_SETPOINT,
        translation_key="hot_water_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_MAX_CH_SETPOINT,
        translation_key="max_central_heating_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_OEM_DIAG,
        translation_key="oem_diagnostic_code",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_TOTAL_BURNER_STARTS,
        translation_key="total_burner_starts",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="starts",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CH_PUMP_STARTS,
        translation_key="central_heating_pump_starts",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="starts",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_PUMP_STARTS,
        translation_key="hot_water_pump_starts",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="starts",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_BURNER_STARTS,
        translation_key="hot_water_burner_starts",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="starts",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_TOTAL_BURNER_HOURS,
        translation_key="total_burner_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_CH_PUMP_HOURS,
        translation_key="central_heating_pump_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_PUMP_HOURS,
        translation_key="hot_water_pump_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_DHW_BURNER_HOURS,
        translation_key="hot_water_burner_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_OT_VERSION,
        translation_key="opentherm_version",
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_PRODUCT_TYPE,
        translation_key="product_type",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_SLAVE_PRODUCT_VERSION,
        translation_key="product_version",
        device_description=BOILER_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_MODE,
        translation_key="operating_mode",
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_DHW_OVRD,
        translation_key="hot_water_override_mode",
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_ABOUT,
        translation_key="firmware_version",
        make_state_lowercase=False,
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_BUILD,
        translation_key="firmware_build",
        make_state_lowercase=False,
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_CLOCKMHZ,
        translation_key="clock_speed",
        make_state_lowercase=False,
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_A,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "A"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_B,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "B"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_C,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "C"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_D,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "D"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_E,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "E"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_LED_F,
        translation_key="led_mode_n",
        translation_placeholders={"led_id": "F"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_GPIO_A,
        translation_key="gpio_mode_n",
        translation_placeholders={"gpio_id": "A"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_GPIO_B,
        translation_key="gpio_mode_n",
        translation_placeholders={"gpio_id": "B"},
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_SB_TEMP,
        translation_key="setback_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_SETP_OVRD_MODE,
        translation_key="room_setpoint_override_mode",
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_SMART_PWR,
        translation_key="smart_power_mode",
        make_state_lowercase=False,
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_THRM_DETECT,
        translation_key="thermostat_detection_mode",
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.OTGW_VREF,
        translation_key="reference_voltage",
        device_description=GATEWAY_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_MASTER_MEMBERID,
        translation_key="manufacturer_id",
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_ROOM_SETPOINT_OVRD,
        translation_key="room_setpoint_override",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_ROOM_SETPOINT,
        translation_key="room_setpoint_n",
        translation_placeholders={"setpoint_id": "1"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_ROOM_SETPOINT_2,
        translation_key="room_setpoint_n",
        translation_placeholders={"setpoint_id": "2"},
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_ROOM_TEMP,
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_OUTSIDE_TEMP,
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_MASTER_OT_VERSION,
        translation_key="opentherm_version",
        suggested_display_precision=SENSOR_FLOAT_SUGGESTED_DISPLAY_PRECISION,
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_MASTER_PRODUCT_TYPE,
        translation_key="product_type",
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
    OpenThermSensorEntityDescription(
        key=gw_vars.DATA_MASTER_PRODUCT_VERSION,
        translation_key="product_version",
        device_description=THERMOSTAT_DEVICE_DESCRIPTION,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OpenTherm Gateway sensors."""
    gw_hub = hass.data[DATA_OPENTHERM_GW][DATA_GATEWAYS][config_entry.data[CONF_ID]]

    async_add_entities(
        OpenThermSensor(
            gw_hub,
            description,
        )
        for description in SENSOR_DESCRIPTIONS
    )


class OpenThermSensor(OpenThermEntity, SensorEntity):
    """Representation of an OpenTherm sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    entity_description: OpenThermSensorEntityDescription

    @callback
    def receive_report(self, status: dict[OpenThermDataSource, dict]) -> None:
        """Handle status updates from the component."""
        value = status[self.entity_description.device_description.data_source].get(
            self.entity_description.key
        )
        if isinstance(value, str) and self.entity_description.make_state_lowercase:
            value = value.lower()
        self._attr_native_value = value
        self.async_write_ha_state()
