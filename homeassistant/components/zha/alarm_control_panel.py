"""Alarm control panels on Zigbee Home Automation networks."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ZHAEntity
from .helpers import get_zha_data


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zigbee Home Automation alarm control panel from config entry."""
    zha_data = get_zha_data(hass)
    entities_to_create = zha_data.platforms.pop(Platform.ALARM_CONTROL_PANEL, [])
    async_add_entities(entities_to_create)


class ZHAAlarmControlPanel(ZHAEntity, AlarmControlPanelEntity):
    """Entity for ZHA alarm control devices."""

    _attr_translation_key: str = "alarm_control_panel"
    _attr_code_format = CodeFormat.TEXT
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return self.entity_data.entity.code_arm_required

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self.entity_data.entity.async_alarm_disarm(code)
        self.async_write_ha_state()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self.entity_data.entity.async_alarm_arm_home(code)
        self.async_write_ha_state()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self.entity_data.entity.async_alarm_arm_away(code)
        self.async_write_ha_state()

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        self.entity_data.entity.async_alarm_arm_night(code)
        self.async_write_ha_state()

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""
        self.entity_data.entity.async_alarm_trigger(code)
        self.async_write_ha_state()

    @property
    def state(self) -> str | None:
        """Return the state of the entity."""
        return self.entity_data.entity.state
