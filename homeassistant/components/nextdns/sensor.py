"""Support for the NextDNS service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NextDnsUpdateCoordinator
from .const import (
    ATTR_DNSSEC,
    ATTR_ENCRYPTION,
    ATTR_IP_VERSIONS,
    ATTR_PROTOCOLS,
    ATTR_STATUS,
    DOMAIN,
)

PARALLEL_UPDATES = 1


@dataclass
class NextDnsSensorRequiredKeysMixin:
    """Class for NextDNS entity required keys."""

    coordinator_type: str


@dataclass
class NextDnsSensorEntityDescription(
    SensorEntityDescription, NextDnsSensorRequiredKeysMixin
):
    """NextDNS sensor entity description."""


SENSORS = (
    NextDnsSensorEntityDescription(
        key="all_queries",
        coordinator_type=ATTR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:dns",
        name="{profile_name} DNS Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="blocked_queries",
        coordinator_type=ATTR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:dns",
        name="{profile_name} DNS Queries Blocked",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="relayed_queries",
        coordinator_type=ATTR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:dns",
        name="{profile_name} DNS Queries Relayed",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="blocked_queries_ratio",
        coordinator_type=ATTR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:dns",
        name="{profile_name} DNS Queries Blocked Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="doh_queries",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} DNS-over-HTTPS Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="dot_queries",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} DNS-over-TLS Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="doq_queries",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} DNS-over-QUIC Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="udp_queries",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} UDP Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="doh_queries_ratio",
        coordinator_type=ATTR_PROTOCOLS,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="{profile_name} DNS-over-HTTPS Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="dot_queries_ratio",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} DNS-over-TLS Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="doq_queries_ratio",
        coordinator_type=ATTR_PROTOCOLS,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="{profile_name} DNS-over-QUIC Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="udp_queries_ratio",
        coordinator_type=ATTR_PROTOCOLS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:dns",
        name="{profile_name} UDP Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="encrypted_queries",
        coordinator_type=ATTR_ENCRYPTION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock",
        name="{profile_name} Encrypted Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="unencrypted_queries",
        coordinator_type=ATTR_ENCRYPTION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock-open",
        name="{profile_name} Unncrypted Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="encrypted_queries_ratio",
        coordinator_type=ATTR_ENCRYPTION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock",
        name="{profile_name} Encrypted Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="ipv4_queries",
        coordinator_type=ATTR_IP_VERSIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:ip",
        name="{profile_name} IPv4 Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="ipv6_queries",
        coordinator_type=ATTR_IP_VERSIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:ip",
        name="{profile_name} IPv6 Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="ipv6_queries_ratio",
        coordinator_type=ATTR_IP_VERSIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:ip",
        name="{profile_name} IPv6 Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="validated_queries",
        coordinator_type=ATTR_DNSSEC,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock-check",
        name="{profile_name} DNSSEC Validated Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="not_validated_queries",
        coordinator_type=ATTR_DNSSEC,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock-alert",
        name="{profile_name} DNSSEC Not Validated Queries",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextDnsSensorEntityDescription(
        key="validated_queries_ratio",
        coordinator_type=ATTR_DNSSEC,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:lock-check",
        name="{profile_name} DNSSEC Validated Queries Ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a NextDNS entities from a config_entry."""
    sensors: list[NextDnsSensor] = []
    coordinators = hass.data[DOMAIN][entry.entry_id]

    for description in SENSORS:
        sensors.append(
            NextDnsSensor(coordinators[description.coordinator_type], description)
        )

    async_add_entities(sensors)


class NextDnsSensor(CoordinatorEntity, SensorEntity):
    """Define an NextDNS sensor."""

    coordinator: NextDnsUpdateCoordinator

    def __init__(
        self,
        coordinator: NextDnsUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.profile_id}-{description.key}"
        self._attr_name = cast(str, description.name).format(
            profile_name=coordinator.profile_name
        )
        self._attr_native_value = getattr(coordinator.data, description.key)
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = getattr(
            self.coordinator.data, self.entity_description.key
        )
        self.async_write_ha_state()
