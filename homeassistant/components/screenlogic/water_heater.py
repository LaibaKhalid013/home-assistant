"""Support for a ScreenLogic Water Heater."""
from screenlogicpy.const import HEAT_MODE

import logging
from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_OPERATION_MODE,
    ATTR_OPERATION_MODE,
)
from homeassistant.const import TEMP_CELSIUS, TEMP_FAHRENHEIT, ATTR_TEMPERATURE

from . import ScreenlogicEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FEATURES = SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

MODE_NAME_TO_MODE_NUM = {
    HEAT_MODE._names[num]: num for num in range(len(HEAT_MODE._names))
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""
    entities = []
    for body in hass.data[DOMAIN][config_entry.unique_id]["devices"]["water_heater"]:
        _LOGGER.info(body)
        entities.append(
            ScreenLogicWaterHeater(
                hass.data[DOMAIN][config_entry.unique_id]["coordinator"], body
            )
        )
    async_add_entities(entities, True)


class ScreenLogicWaterHeater(ScreenlogicEntity, WaterHeaterEntity):
    """Represents the heating functions for a body of water."""

    def __init__(self, coordinator, body):
        super().__init__(coordinator, body)

    @property
    def name(self) -> str:
        """Name of the water heater."""
        ent_name = self.coordinator.data["bodies"][self._entity_id]["heat_status"][
            "name"
        ]
        gateway_name = self.coordinator.gateway.name
        return gateway_name + " " + ent_name

    @property
    def state(self) -> str:
        """Current state of the water heater."""
        return HEAT_MODE.GetFriendlyName(
            self.coordinator.data["bodies"][self._entity_id]["heat_status"]["value"]
        )

    @property
    def min_temp(self) -> float:
        """Returns the minimum allowed temperature."""
        return self.coordinator.data["bodies"][self._entity_id]["min_set_point"][
            "value"
        ]

    @property
    def max_temp(self) -> float:
        """Returns the maximum allowed temperature."""
        return self.coordinator.data["bodies"][self._entity_id]["max_set_point"][
            "value"
        ]

    @property
    def current_temperature(self) -> float:
        """Gets the current water temperature."""
        return self.coordinator.data["bodies"][self._entity_id]["last_temperature"][
            "value"
        ]

    @property
    def target_temperature(self) -> float:
        """Target temperature."""
        return self.coordinator.data["bodies"][self._entity_id]["heat_set_point"][
            "value"
        ]

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return (
            TEMP_CELSIUS
            if self.coordinator.data["config"]["is_celcius"]["value"] == 1
            else TEMP_FAHRENHEIT
        )

    @property
    def current_operation(self) -> str:
        return HEAT_MODE.GetFriendlyName(
            self.coordinator.data["bodies"][self._entity_id]["heat_mode"]["value"]
        )

    @property
    def operation_list(self):
        return HEAT_MODE._names

    @property
    def supported_features(self):
        return SUPPORTED_FEATURES

    async def async_set_temperature(self, **kwargs) -> None:
        """Change the setpoint of the heater."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if self.coordinator.gateway.set_heat_temp(
            int(self._entity_id), int(temperature)
        ):
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("screenlogic set_temperature error")

    async def async_set_operation_mode(self, **kwargs) -> None:
        mode = MODE_NAME_TO_MODE_NUM[kwargs.get(ATTR_OPERATION_MODE)]
        if self.coordinator.gateway.set_heat_mode(int(self._entity_id), int(mode)):
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("screenlogic set_operation_mode error")
