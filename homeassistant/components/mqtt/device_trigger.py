"""Provides device automations for MQTT."""
import logging
from typing import List

import attr
import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.components.automation import AutomationActionType
import homeassistant.components.automation.mqtt as automation_mqtt
from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import (
    ATTR_DISCOVERY_HASH,
    CONF_CONNECTIONS,
    CONF_DEVICE,
    CONF_IDENTIFIERS,
    CONF_PAYLOAD,
    CONF_QOS,
    DOMAIN,
)
from .discovery import MQTT_DISCOVERY_UPDATED, clear_discovery_hash

_LOGGER = logging.getLogger(__name__)

CONF_AUTOMATION_TYPE = "automation_type"
CONF_DISCOVERY_ID = "discovery_id"
CONF_SUBTYPE = "subtype"
CONF_TOPIC = "topic"
DEFAULT_ENCODING = "utf-8"
DEVICE = "device"

MQTT_TRIGGER_BASE = {
    # Trigger when MQTT message is received
    CONF_PLATFORM: DEVICE,
    CONF_DOMAIN: DOMAIN,
}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): DEVICE,
        vol.Required(CONF_DOMAIN): DOMAIN,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_DISCOVERY_ID): str,
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_SUBTYPE): cv.string,
    }
)

TRIGGER_DISCOVERY_SCHEMA = mqtt.MQTT_BASE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_AUTOMATION_TYPE): str,
        vol.Required(CONF_DEVICE): mqtt.MQTT_ENTITY_DEVICE_INFO_SCHEMA,
        vol.Required(CONF_TOPIC): mqtt.valid_subscribe_topic,
        vol.Optional(CONF_PAYLOAD, default=None): vol.Any(None, cv.string),
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_SUBTYPE): cv.string,
    },
    mqtt.validate_device_has_at_least_one_identifier,
)

DEVICE_TRIGGERS = "mqtt_device_triggers"


@attr.s(slots=True)
class AttachedTrigger:
    """Attached trigger settings."""

    action = attr.ib(type=AutomationActionType)
    automation_info = attr.ib(type=dict)
    remove = attr.ib(type=CALLBACK_TYPE)


@attr.s(slots=True)
class Trigger:
    """Device trigger settings."""

    attached_triggers = attr.ib(type=[AttachedTrigger])
    device_id = attr.ib(type=str)
    hass = attr.ib(type=HomeAssistantType)
    payload = attr.ib(type=str)
    qos = attr.ib(type=int)
    subtype = attr.ib(type=str)
    topic = attr.ib(type=str)
    type = attr.ib(type=str)

    async def add_trigger(self, action, automation_info):
        """Add MQTT trigger."""
        attached_trigger = AttachedTrigger(action, automation_info, None)
        self.attached_triggers.append(attached_trigger)

        if self.topic is not None:
            # If we know about the trigger, subscribe to MQTT topic
            attached_trigger.remove = await self.attach_trigger(attached_trigger)

        @callback
        def async_remove() -> None:
            """Remove trigger."""
            if attached_trigger not in self.attached_triggers:
                raise HomeAssistantError("Can't remove trigger twice")

            index = self.attached_triggers.index(attached_trigger)
            if self.attached_triggers[index].remove:
                self.attached_triggers[index].remove()
            self.attached_triggers.pop(index)

        return async_remove

    async def attach_trigger(self, attached_trigger):
        """Attach MQTT trigger."""
        mqtt_config = {
            automation_mqtt.CONF_TOPIC: self.topic,
            automation_mqtt.CONF_ENCODING: DEFAULT_ENCODING,
            automation_mqtt.CONF_QOS: self.qos,
        }
        if self.payload:
            mqtt_config[CONF_PAYLOAD] = self.payload

        return await automation_mqtt.async_attach_trigger(
            self.hass,
            mqtt_config,
            attached_trigger.action,
            attached_trigger.automation_info,
        )

    async def update_trigger(self, config):
        """Update MQTT device trigger."""
        self.type = config[CONF_TYPE]
        self.subtype = config[CONF_SUBTYPE]
        self.topic = config[CONF_TOPIC]
        self.payload = config[CONF_PAYLOAD]
        self.qos = config[CONF_QOS]

        # Unsubscribe+subscribe if this trigger is in use
        for trig in self.attached_triggers:
            if trig.remove:
                trig.remove()
            trig.remove = await self.attach_trigger(trig)

    def detach_trigger(self):
        """Remove MQTT device trigger."""

        # Unsubscribe if this trigger is in use
        for trig in self.attached_triggers:
            if trig.remove:
                trig.remove()


async def _update_device(hass, config_entry, config):
    """Update device registry."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    config_entry_id = config_entry.entry_id
    device_info = mqtt.device_info_from_config(config[CONF_DEVICE])

    if config_entry_id is not None and device_info is not None:
        device_info["config_entry_id"] = config_entry_id
        device_registry.async_get_or_create(**device_info)


async def async_setup_trigger(hass, config, config_entry, discovery_hash):
    """Set up the MQTT device trigger."""
    config = TRIGGER_DISCOVERY_SCHEMA(config)
    discovery_id = discovery_hash[1]
    remove_signal = None

    async def discovery_update(payload):
        """Handle discovery update."""
        _LOGGER.info(
            "Got update for trigger with hash: %s '%s'", discovery_hash, payload
        )
        if not payload:
            # Empty payload: Remove trigger
            _LOGGER.info("Removing trigger: %s", discovery_hash)
            device_trigger = hass.data[DEVICE_TRIGGERS].pop(discovery_id)

            if device_trigger:
                device_trigger.detach_trigger()
                clear_discovery_hash(hass, discovery_hash)
                remove_signal()
        else:
            # Non-empty payload: Update trigger
            _LOGGER.info("Updating trigger: %s", discovery_hash)
            payload.pop(ATTR_DISCOVERY_HASH)
            config = TRIGGER_DISCOVERY_SCHEMA(payload)
            await _update_device(hass, config_entry, config)
            device_trigger = hass.data[DEVICE_TRIGGERS][discovery_id]
            await device_trigger.update_trigger(config)

    remove_signal = async_dispatcher_connect(
        hass, MQTT_DISCOVERY_UPDATED.format(discovery_hash), discovery_update
    )

    await _update_device(hass, config_entry, config)

    device_registry = await hass.helpers.device_registry.async_get_registry()
    device = device_registry.async_get_device(
        {(DOMAIN, id_) for id_ in config[CONF_DEVICE][CONF_IDENTIFIERS]},
        {tuple(x) for x in config[CONF_DEVICE][CONF_CONNECTIONS]},
    )

    if device is None:
        return

    if DEVICE_TRIGGERS not in hass.data:
        hass.data[DEVICE_TRIGGERS] = {}
    if discovery_id not in hass.data[DEVICE_TRIGGERS]:
        hass.data[DEVICE_TRIGGERS][discovery_id] = Trigger(
            attached_triggers=[],
            hass=hass,
            device_id=device.id,
            type=config[CONF_TYPE],
            subtype=config[CONF_SUBTYPE],
            topic=config[CONF_TOPIC],
            payload=config[CONF_PAYLOAD],
            qos=config[CONF_QOS],
        )
    else:
        await hass.data[DEVICE_TRIGGERS][discovery_id].update_trigger(config)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for MQTT devices."""
    triggers = []

    if DEVICE_TRIGGERS not in hass.data:
        return triggers

    for discovery_id, trig in hass.data[DEVICE_TRIGGERS].items():
        if trig.device_id != device_id or trig.topic is None:
            continue

        trigger = {
            **MQTT_TRIGGER_BASE,
            "device_id": device_id,
            "type": trig.type,
            "subtype": trig.subtype,
            "discovery_id": discovery_id,
        }
        triggers.append(trigger)

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    if DEVICE_TRIGGERS not in hass.data:
        hass.data[DEVICE_TRIGGERS] = {}
    config = TRIGGER_SCHEMA(config)
    device_id = config[CONF_DEVICE_ID]
    discovery_id = config[CONF_DISCOVERY_ID]

    if discovery_id not in hass.data[DEVICE_TRIGGERS]:
        hass.data[DEVICE_TRIGGERS][discovery_id] = Trigger(
            attached_triggers=[],
            hass=hass,
            device_id=device_id,
            type=config[CONF_TYPE],
            subtype=config[CONF_SUBTYPE],
            topic=None,
            payload=None,
            qos=None,
        )
    return await hass.data[DEVICE_TRIGGERS][discovery_id].add_trigger(
        action, automation_info
    )
