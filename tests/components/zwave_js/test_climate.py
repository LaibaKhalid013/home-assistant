"""Test the Z-Wave JS climate platform."""
from zwave_js_server.event import Event

from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_IDLE,
    DOMAIN as CLIMATE_DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_NONE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE

CLIMATE_RADIO_THERMOSTAT_ENTITY = "climate.z_wave_thermostat_thermostat_mode"


async def test_thermostat_v2(
    hass, client, climate_radio_thermostat_ct100_plus, integration
):
    """Test a thermostat v2 command class entity."""
    node = climate_radio_thermostat_ct100_plus
    state = hass.states.get(CLIMATE_RADIO_THERMOSTAT_ENTITY)

    assert state
    assert state.state == HVAC_MODE_HEAT
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVAC_MODE_OFF,
        HVAC_MODE_HEAT,
        HVAC_MODE_COOL,
        HVAC_MODE_HEAT_COOL,
    ]
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 22.2
    assert state.attributes[ATTR_TEMPERATURE] == 22.2
    assert state.attributes[ATTR_HVAC_ACTION] == CURRENT_HVAC_IDLE
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_NONE

    # Test setting preset mode
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {
            ATTR_ENTITY_ID: CLIMATE_RADIO_THERMOSTAT_ENTITY,
            ATTR_PRESET_MODE: PRESET_NONE,
        },
        blocking=True,
    )

    assert len(client.async_send_command.call_args_list) == 1
    args = client.async_send_command.call_args[0][0]
    assert args["command"] == "node.set_value"
    assert args["nodeId"] == 13
    assert args["valueId"] == {
        "commandClassName": "Thermostat Mode",
        "commandClass": 64,
        "endpoint": 1,
        "property": "mode",
        "propertyName": "mode",
        "metadata": {
            "type": "number",
            "readable": True,
            "writeable": True,
            "min": 0,
            "max": 31,
            "label": "Thermostat mode",
            "states": {"0": "Off", "1": "Heat", "2": "Cool", "3": "Auto"},
        },
        "value": 1,
    }
    assert args["value"] == 1

    client.async_send_command.reset_mock()

    # Test setting hvac mode
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {
            ATTR_ENTITY_ID: CLIMATE_RADIO_THERMOSTAT_ENTITY,
            ATTR_HVAC_MODE: HVAC_MODE_COOL,
        },
        blocking=True,
    )

    assert len(client.async_send_command.call_args_list) == 1
    args = client.async_send_command.call_args[0][0]
    assert args["command"] == "node.set_value"
    assert args["nodeId"] == 13
    assert args["valueId"] == {
        "commandClassName": "Thermostat Mode",
        "commandClass": 64,
        "endpoint": 1,
        "property": "mode",
        "propertyName": "mode",
        "metadata": {
            "type": "number",
            "readable": True,
            "writeable": True,
            "min": 0,
            "max": 31,
            "label": "Thermostat mode",
            "states": {"0": "Off", "1": "Heat", "2": "Cool", "3": "Auto"},
        },
        "value": 1,
    }
    assert args["value"] == 2

    client.async_send_command.reset_mock()

    # Test setting temperature
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: CLIMATE_RADIO_THERMOSTAT_ENTITY, ATTR_TEMPERATURE: 25},
        blocking=True,
    )

    assert len(client.async_send_command.call_args_list) == 1
    args = client.async_send_command.call_args[0][0]
    assert args["command"] == "node.set_value"
    assert args["nodeId"] == 13
    assert args["valueId"] == {
        "commandClassName": "Thermostat Setpoint",
        "commandClass": 67,
        "endpoint": 1,
        "property": "setpoint",
        "propertyKey": 1,
        "propertyName": "setpoint",
        "propertyKeyName": "Heating",
        "metadata": {
            "type": "number",
            "readable": True,
            "writeable": True,
            "unit": "°F",
            "ccSpecific": {"setpointType": 1},
        },
        "value": 72,
    }
    assert args["value"] == 77

    client.async_send_command.reset_mock()

    # Test cool mode update from value updated event
    event = Event(
        type="value updated",
        data={
            "source": "node",
            "event": "value updated",
            "nodeId": 13,
            "args": {
                "commandClassName": "Thermostat Mode",
                "commandClass": 64,
                "endpoint": 1,
                "property": "mode",
                "propertyName": "mode",
                "newValue": 2,
                "prevValue": 1,
            },
        },
    )
    node.receive_event(event)

    state = hass.states.get(CLIMATE_RADIO_THERMOSTAT_ENTITY)
    assert state.state == HVAC_MODE_COOL
    assert state.attributes[ATTR_TEMPERATURE] == 22.8

    # Test heat_cool mode update from value updated event
    event = Event(
        type="value updated",
        data={
            "source": "node",
            "event": "value updated",
            "nodeId": 13,
            "args": {
                "commandClassName": "Thermostat Mode",
                "commandClass": 64,
                "endpoint": 1,
                "property": "mode",
                "propertyName": "mode",
                "newValue": 3,
                "prevValue": 1,
            },
        },
    )
    node.receive_event(event)

    state = hass.states.get(CLIMATE_RADIO_THERMOSTAT_ENTITY)
    assert state.state == HVAC_MODE_HEAT_COOL
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 22.8
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 22.2
