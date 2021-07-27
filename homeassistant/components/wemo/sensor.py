"""Support for power sensors in WeMo Insight devices."""
import asyncio
from datetime import datetime, timedelta
from typing import Callable

from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import StateType
from homeassistant.util import Throttle, convert, dt

from .const import DOMAIN as WEMO_DOMAIN
from .entity import WemoSubscriptionEntity
from .wemo_device import DeviceWrapper

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up WeMo sensors."""

    async def _discovered_wemo(device: DeviceWrapper):
        """Handle a discovered Wemo device."""

        @Throttle(SCAN_INTERVAL)
        def update_insight_params():
            device.wemo.update_insight_params()

        async_add_entities(
            [
                InsightCurrentPower(device, update_insight_params),
                InsightTodayEnergy(device, update_insight_params),
            ]
        )

    async_dispatcher_connect(hass, f"{WEMO_DOMAIN}.sensor", _discovered_wemo)

    await asyncio.gather(
        *(
            _discovered_wemo(device)
            for device in hass.data[WEMO_DOMAIN]["pending"].pop("sensor")
        )
    )


class InsightSensor(WemoSubscriptionEntity, SensorEntity):
    """Common base for WeMo Insight power sensors."""

    _attr_state_class = STATE_CLASS_MEASUREMENT
    _name_suffix: str
    _insight_device_key: str

    def __init__(self, device: DeviceWrapper, update_insight_params: Callable) -> None:
        """Initialize the WeMo Insight power sensor."""
        super().__init__(device)
        self._update_insight_params = update_insight_params

    @property
    def name(self) -> str:
        """Return the name of the entity if any."""
        return f"{self.wemo.name} {self._name_suffix}"

    @property
    def unique_id(self) -> str:
        """Return the id of this entity."""
        return f"{self.wemo.serialnumber}_{self._name_suffix}"

    @property
    def available(self) -> str:
        """Return true if sensor is available."""
        return (
            self._insight_device_key in self.wemo.insight_params and super().available
        )

    def _update(self, force_update=True) -> None:
        with self._wemo_exception_handler("update status"):
            if force_update or not self.wemo.insight_params:
                self._update_insight_params()


class InsightCurrentPower(InsightSensor):
    """Current instantaineous power consumption."""

    _attr_device_class = DEVICE_CLASS_POWER
    _attr_unit_of_measurement = POWER_WATT
    _name_suffix = "Current Power"
    _insight_device_key = "currentpower"

    @property
    def state(self) -> StateType:
        """Return the current power consumption."""
        return (
            convert(self.wemo.insight_params[self._insight_device_key], float, 0.0)
            / 1000.0
        )


class InsightTodayEnergy(InsightSensor):
    """Energy used today."""

    _attr_device_class = DEVICE_CLASS_ENERGY
    _attr_unit_of_measurement = ENERGY_KILO_WATT_HOUR
    _name_suffix = "Today Energy"
    _insight_device_key = "todaymw"

    @property
    def last_reset(self) -> datetime:
        """Return the time when the sensor was initialized."""
        return dt.start_of_local_day()

    @property
    def state(self) -> StateType:
        """Return the current energy use today."""
        miliwatts = convert(
            self.wemo.insight_params[self._insight_device_key], float, 0.0
        )
        return round(miliwatts / (1000.0 * 1000.0 * 60), 2)
