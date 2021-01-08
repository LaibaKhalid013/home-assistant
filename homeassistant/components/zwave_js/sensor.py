"""Representation of Z-Wave sensors."""

import logging

from zwave_js_server.client import Client as ZwaveClient
from zwave_js_server.const import CommandClass

from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.const import TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DATA_CLIENT, DATA_PLATFORM_READY, DATA_UNSUBSCRIBE, DOMAIN
from .discovery import ZwaveDiscoveryInfo
from .entity import ZWaveBaseEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Z-Wave sensor from config entry."""
    client: ZwaveClient = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]
    platform_ready = hass.data[DOMAIN][config_entry.entry_id][DATA_PLATFORM_READY]

    @callback
    def async_add_sensor(info: ZwaveDiscoveryInfo):
        """Add Z-Wave Sensor."""
        if info.platform_hint == "string_sensor":
            sensor = ZWaveStringSensor(client, info)
        if info.platform_hint == "numeric_sensor":
            sensor = ZWaveNumericSensor(client, info)
        else:
            LOGGER.warning(
                "Sensor not implemented for %s/%s",
                info.platform_hint,
                info.primary_value.propertyname,
            )
            return
        async_add_entities([sensor])

    hass.data[DOMAIN][config_entry.entry_id][DATA_UNSUBSCRIBE].append(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_add_{SENSOR_DOMAIN}", async_add_sensor
        )
    )

    platform_ready()


class ZwaveSensorBase(ZWaveBaseEntity):
    """Basic Representation of a Z-Wave sensor."""

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self.info.primary_value.command_class == CommandClass.BATTERY:
            return DEVICE_CLASS_BATTERY
        if self.info.primary_value.command_class == CommandClass.METER:
            return DEVICE_CLASS_POWER
        if self.info.primary_value.property_key_name == "W_Consumed":
            return DEVICE_CLASS_POWER
        if self.info.primary_value.property_key_name == "kWh_Consumed":
            return DEVICE_CLASS_ENERGY
        return self.info.primary_value.property_

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        # We hide some of the more advanced sensors by default to not overwhelm users
        if self.info.primary_value.command_class in [
            CommandClass.BASIC,
            CommandClass.INDICATOR,
            CommandClass.NOTIFICATION,
        ]:
            return False
        return True

    @property
    def force_update(self) -> bool:
        """Force updates."""
        return True


class ZWaveStringSensor(ZwaveSensorBase):
    """Representation of a Z-Wave String sensor."""

    @property
    def state(self) -> str:
        """Return state of the sensor."""
        return self.info.primary_value.value

    @property
    def unit_of_measurement(self) -> str:
        """Return unit of measurement the value is expressed in."""
        return self.info.primary_value.metadata.unit


class ZWaveNumericSensor(ZwaveSensorBase):
    """Representation of a Z-Wave Numeric sensor."""

    @property
    def state(self) -> str:
        """Return state of the sensor."""
        if self.info.primary_value.value is None:
            return 0
        return round(self.info.primary_value.value, 2)

    @property
    def unit_of_measurement(self) -> str:
        """Return unit of measurement the value is expressed in."""

        if self.info.primary_value.metadata.unit == "C":
            return TEMP_CELSIUS
        if self.info.primary_value.metadata.unit == "F":
            return TEMP_FAHRENHEIT

        return self.info.primary_value.metadata.unit

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        if (
            self.info.primary_value.metadata.states
            and self.info.primary_value.value is not None
        ):
            # add the value's label as property for multi-value (list) items
            label = self.info.primary_value.metadata.states.get(
                self.info.primary_value.value
            ) or self.info.primary_value.metadata.states.get(
                str(self.info.primary_value.value)
            )
            return {"label": label}
