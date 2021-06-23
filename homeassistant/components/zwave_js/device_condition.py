"""Provide the device conditions for Z-Wave JS."""
from __future__ import annotations

from typing import cast

import voluptuous as vol
from zwave_js_server.const import CommandClass, ConfigurationValueType
from zwave_js_server.model.value import ConfigurationValue, get_value_id

from homeassistant.components.zwave_js.const import (
    ATTR_COMMAND_CLASS,
    ATTR_ENDPOINT,
    ATTR_PROPERTY,
    ATTR_PROPERTY_KEY,
    ATTR_VALUE,
)
from homeassistant.const import CONF_CONDITION, CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import condition, config_validation as cv
from homeassistant.helpers.config_validation import DEVICE_CONDITION_BASE_SCHEMA
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN
from .helpers import async_get_node_from_device_id

CONF_SUBTYPE = "subtype"

CONF_VALUE_ID = "value_id"

NODE_STATUS_TYPES = {"asleep", "awake", "dead", "alive"}
CONFIG_PARAMETER_TYPE = "config_parameter"
VALUE_TYPE = "value"
CONDITION_TYPES = {*NODE_STATUS_TYPES, CONFIG_PARAMETER_TYPE, VALUE_TYPE}

NODE_STATUS_CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(NODE_STATUS_TYPES),
    }
)

CONFIG_PARAMETER_CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): CONFIG_PARAMETER_TYPE,
        vol.Required(CONF_VALUE_ID): cv.string,
        vol.Required(CONF_SUBTYPE): cv.string,
        vol.Optional(ATTR_VALUE): vol.Coerce(int),
    }
)

VALUE_CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): VALUE_TYPE,
        vol.Required(ATTR_COMMAND_CLASS): vol.In([cc.name for cc in CommandClass]),
        vol.Required(ATTR_PROPERTY): vol.Any(vol.Coerce(int), cv.string),
        vol.Optional(ATTR_PROPERTY_KEY): vol.Any(vol.Coerce(int), cv.string),
        vol.Optional(ATTR_ENDPOINT): vol.Coerce(int),
        vol.Required(ATTR_VALUE): vol.Any(
            bool,
            vol.Coerce(int),
            vol.Coerce(float),
            cv.boolean,
            cv.string,
        ),
    }
)

CONDITION_SCHEMA = vol.Any(
    NODE_STATUS_CONDITION_SCHEMA,
    CONFIG_PARAMETER_CONDITION_SCHEMA,
    VALUE_CONDITION_SCHEMA,
)


async def async_get_conditions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device conditions for Z-Wave JS devices."""
    conditions = []
    base_condition = {
        CONF_CONDITION: "device",
        CONF_DEVICE_ID: device_id,
        CONF_DOMAIN: DOMAIN,
    }
    node = async_get_node_from_device_id(hass, device_id)

    # Any value's value condition
    conditions.append({**base_condition, CONF_TYPE: VALUE_TYPE})

    # Node status conditions
    conditions.extend(
        [{**base_condition, CONF_TYPE: cond} for cond in NODE_STATUS_TYPES]
    )

    # Config parameter conditions
    conditions.extend(
        [
            {
                **base_condition,
                CONF_VALUE_ID: config_value.value_id,
                CONF_TYPE: CONFIG_PARAMETER_TYPE,
                CONF_SUBTYPE: f"{config_value.value_id} ({config_value.property_name})",
            }
            for config_value in node.get_configuration_values().values()
        ]
    )

    return conditions


@callback
def async_condition_from_config(
    config: ConfigType, config_validation: bool
) -> condition.ConditionCheckerType:
    """Create a function to test a device condition."""
    if config_validation:
        config = CONDITION_SCHEMA(config)

    condition_type = config[CONF_TYPE]
    device_id = config[CONF_DEVICE_ID]

    @callback
    def test_node_status(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
        """Test if node status is a certain state."""
        node = async_get_node_from_device_id(hass, device_id)
        return bool(node.status.name.lower() == condition_type)

    if condition_type in NODE_STATUS_TYPES:
        return test_node_status

    @callback
    def test_config_parameter(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
        """Test if config parameter is a certain state."""
        node = async_get_node_from_device_id(hass, device_id)
        config_value = cast(ConfigurationValue, node.values[config[CONF_VALUE_ID]])
        return bool(config_value.value == config[ATTR_VALUE])

    if condition_type == CONFIG_PARAMETER_TYPE:
        return test_config_parameter

    @callback
    def test_value(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
        """Test if value is a certain state."""
        node = async_get_node_from_device_id(hass, device_id)
        value_id = get_value_id(
            node,
            CommandClass[config[ATTR_COMMAND_CLASS]],
            config[ATTR_PROPERTY],
            config.get(ATTR_ENDPOINT) or None,
            config.get(ATTR_PROPERTY_KEY) or None,
        )
        value = node.values[value_id]
        return bool(value.value == config[ATTR_VALUE])

    if condition_type == VALUE_TYPE:
        return test_value

    raise HomeAssistantError(f"Unhandled condition type {condition_type}")


@callback
async def async_get_condition_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List condition capabilities."""
    device_id = config[CONF_DEVICE_ID]
    node = async_get_node_from_device_id(hass, device_id)

    # Add additional fields to the automation trigger UI
    if config[CONF_TYPE] == CONFIG_PARAMETER_TYPE:
        value_id = config[CONF_VALUE_ID]
        config_value = cast(ConfigurationValue, node.values[value_id])
        min = config_value.metadata.min
        max = config_value.metadata.max

        if config_value.configuration_value_type == ConfigurationValueType.RANGE:
            value_schema = vol.Range(min=min, max=max)
        elif (
            config_value.configuration_value_type == ConfigurationValueType.MANUAL_ENTRY
        ):
            value_schema = (
                vol.In(
                    {
                        i: config_value.metadata.states.get(str(i)) or i
                        for i in range(min, max + 1)
                    }
                )
                if config_value.metadata.states
                else vol.Range(min=min, max=max)
            )
        elif config_value.configuration_value_type == ConfigurationValueType.ENUMERATED:
            value_schema = vol.In(
                {int(k): v for k, v in config_value.metadata.states.items()}
            )
        else:
            return {}

        return {"extra_fields": vol.Schema({vol.Required(ATTR_VALUE): value_schema})}

    if config[CONF_TYPE] == VALUE_TYPE:
        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required(ATTR_COMMAND_CLASS): vol.In(
                        [cc.name for cc in CommandClass]
                    ),
                    vol.Required(ATTR_PROPERTY): cv.string,
                    vol.Optional(ATTR_PROPERTY_KEY): cv.string,
                    vol.Optional(ATTR_ENDPOINT): cv.string,
                    vol.Required(ATTR_VALUE): cv.string,
                }
            )
        }

    return {}
