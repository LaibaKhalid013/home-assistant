"""Provides device automations for Alarm control panel."""
from typing import List
import voluptuous as vol

from homeassistant.const import (
    CONF_DOMAIN,
    CONF_TYPE,
    CONF_PLATFORM,
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers import config_validation as cv, entity_registry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.automation import state, AutomationActionType
from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA
from . import DOMAIN

TRIGGER_TYPES = {
    "pending",
    "triggered",
    "disarmed",
    "armed_home",
    "armed_away",
    "armed_night",
}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Alarm control panel devices."""
    registry = await entity_registry.async_get_registry(hass)
    triggers = []

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        # Add triggers for each entity that belongs to this integration
        for trigger_type in TRIGGER_TYPES:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: trigger_type,
                }
            )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    config = TRIGGER_SCHEMA(config)

    if config[CONF_TYPE] == "pending":
        from_state = STATE_ALARM_DISARMED
        to_state = STATE_ALARM_PENDING
    elif config[CONF_TYPE] == "triggered":
        from_state = STATE_ALARM_PENDING
        to_state = STATE_ALARM_TRIGGERED
    elif config[CONF_TYPE] == "disarmed":
        from_state = STATE_ALARM_TRIGGERED
        to_state = STATE_ALARM_DISARMED
    elif config[CONF_TYPE] == "armed_home":
        from_state = STATE_ALARM_PENDING
        to_state = STATE_ALARM_ARMED_HOME
    elif config[CONF_TYPE] == "armed_away":
        from_state = STATE_ALARM_PENDING
        to_state = STATE_ALARM_ARMED_AWAY
    elif config[CONF_TYPE] == "armed_night":
        from_state = STATE_ALARM_PENDING
        to_state = STATE_ALARM_ARMED_NIGHT

    state_config = {
        state.CONF_PLATFORM: "state",
        CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        state.CONF_FROM: from_state,
        state.CONF_TO: to_state,
    }
    state_config = state.TRIGGER_SCHEMA(state_config)
    return await state.async_attach_trigger(
        hass, state_config, action, automation_info, platform_type="device"
    )
