"""Support for Fast.com internet speed testing sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DATA_UPDATED, DOMAIN as FASTDOTCOM_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Fast.com sensor."""
    async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{FASTDOTCOM_DOMAIN}",
        breaks_in_ha_version="2023.12.0",
        is_fixable=False,
        issue_domain=FASTDOTCOM_DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": FASTDOTCOM_DOMAIN,
            "integration_title": "Fast.com",
        },
    )
    async_add_entities([SpeedtestSensor(hass.data[FASTDOTCOM_DOMAIN])])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fast.com sensor."""
    _LOGGER.debug("Setting up Fast.com sensor with domain %s", FASTDOTCOM_DOMAIN)
    # get this working!
    # hass.data[DOMAIN][entry.entry_id]
    # async_add_entities([SpeedtestSensor(api)])


# pylint: disable-next=hass-invalid-inheritance # needs fixing
class SpeedtestSensor(RestoreEntity, SensorEntity):
    """Implementation of a Fast.com sensor."""

    _attr_name = "Fast.com Download"
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:speedometer"
    _attr_should_poll = False

    def __init__(self, speedtest_data: dict[str, Any]) -> None:
        """Initialize the sensor."""
        self._speedtest_data = speedtest_data

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, DATA_UPDATED, self._schedule_immediate_update
            )
        )

        if not (state := await self.async_get_last_state()):
            return
        self._attr_native_value = state.state

    def update(self) -> None:
        """Get the latest data and update the states."""
        if (data := self._speedtest_data.data) is None:  # type: ignore[attr-defined]
            return
        self._attr_native_value = data["download"]

    @callback
    def _schedule_immediate_update(self) -> None:
        self.async_schedule_update_ha_state(True)
