"""Support for monitoring emoncms feeds."""

from __future__ import annotations

from typing import Any

from pyemoncms import EmoncmsClient
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_ID,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_URL,
    CONF_VALUE_TEMPLATE,
    STATE_UNKNOWN,
    Platform,
    UnitOfPower,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, template
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_EXCLUDE_FEEDID,
    CONF_ONLY_INCLUDE_FEEDID,
    CONF_SENSOR_NAMES,
    DOMAIN,
    LOGGER,
)
from .coordinator import EmoncmsCoordinator

ATTR_FEEDID = "FeedId"
ATTR_FEEDNAME = "FeedName"
ATTR_LASTUPDATETIME = "LastUpdated"
ATTR_LASTUPDATETIMESTR = "LastUpdatedStr"
ATTR_SIZE = "Size"
ATTR_TAG = "Tag"
ATTR_USERID = "UserId"

DECIMALS = 2
DEFAULT_UNIT = UnitOfPower.WATT

ONLY_INCL_EXCL_NONE = "only_include_exclude_or_none"

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Required(CONF_ID): cv.positive_int,
        vol.Exclusive(CONF_ONLY_INCLUDE_FEEDID, ONLY_INCL_EXCL_NONE): vol.All(
            cv.ensure_list, [cv.positive_int]
        ),
        vol.Exclusive(CONF_EXCLUDE_FEEDID, ONLY_INCL_EXCL_NONE): vol.All(
            cv.ensure_list, [cv.positive_int]
        ),
        vol.Optional(CONF_SENSOR_NAMES): vol.All(
            {cv.positive_int: vol.All(cv.string, vol.Length(min=1))}
        ),
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=DEFAULT_UNIT): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import config from yaml."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=config
    )
    if (
        result.get("type") == FlowResultType.CREATE_ENTRY
        or result.get("reason") == "already_configured"
    ):
        async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            issue_domain=DOMAIN,
            breaks_in_ha_version="2025.2.0",
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "emoncms",
            },
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the emoncms sensors."""
    LOGGER.debug(f"WE ARE IN ASYNC_STEP_ENTRY : {entry}")
    config = entry.data
    apikey = config[CONF_API_KEY]
    url = config[CONF_URL]
    sensorid = config[CONF_ID]
    value_template = None
    if config.get(CONF_VALUE_TEMPLATE) is not None:
        value_template = template.Template(config[CONF_VALUE_TEMPLATE])
    config_unit = config.get(CONF_UNIT_OF_MEASUREMENT)
    exclude_feeds = config.get(CONF_EXCLUDE_FEEDID)
    include_only_feeds = config.get(CONF_ONLY_INCLUDE_FEEDID)
    sensor_names = config.get(CONF_SENSOR_NAMES)

    if exclude_feeds is None and include_only_feeds is None:
        return

    if value_template is not None:
        value_template.hass = hass

    emoncms_client = EmoncmsClient(url, apikey, session=async_get_clientsession(hass))
    emoncms_unique_id = await emoncms_client.async_get_uuid()
    if emoncms_unique_id is None:
        async_create_issue(
            hass,
            DOMAIN,
            "migrate_database",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="migrate_database",
            translation_placeholders={"url": url},
        )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    elems = coordinator.data
    if elems is None:
        return
    ent_reg = er.async_get(hass)
    sensors: list[EmonCmsSensor] = []

    for idx, elem in enumerate(elems):
        if exclude_feeds is not None and elem["id"] in exclude_feeds:
            continue

        if include_only_feeds is not None and elem["id"] not in include_only_feeds:
            continue

        entity_id = ent_reg.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{entry.entry_id}-{elem['id']}"
        )
        if entity_id is not None and emoncms_unique_id is not None:
            LOGGER.debug(f"{entity_id} exists and needs to be migrated")
            ent_reg.async_update_entity(
                entity_id, new_unique_id=f"{emoncms_unique_id}-{elem['id']}"
            )
        name = None
        if sensor_names is not None:
            name = sensor_names.get(int(elem["id"]), None)

        if unit := elem.get("unit"):
            unit_of_measurement = unit
        else:
            unit_of_measurement = config_unit

        sensors.append(
            EmonCmsSensor(
                coordinator,
                emoncms_unique_id,
                entry.entry_id,
                name,
                value_template,
                unit_of_measurement,
                str(sensorid),
                idx,
            )
        )
    async_add_entities(sensors)


class EmonCmsSensor(CoordinatorEntity[EmoncmsCoordinator], SensorEntity):
    """Implementation of an Emoncms sensor."""

    def __init__(
        self,
        coordinator: EmoncmsCoordinator,
        emoncms_unique_id: str,
        unique_id: str,
        name: str | None,
        value_template: template.Template | None,
        unit_of_measurement: str | None,
        sensorid: str,
        idx: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.idx = idx
        elem = {}
        if self.coordinator.data:
            elem = self.coordinator.data[self.idx]
        if name is None:
            # Suppress ID in sensor name if it's 1, since most people won't
            # have more than one EmonCMS source and it's redundant to show the
            # ID if there's only one.
            id_for_name = "" if str(sensorid) == "1" else sensorid
            # Use the feed name assigned in EmonCMS or fall back to the feed ID
            feed_name = elem.get("name", f"Feed {elem.get('id')}")
            self._attr_name = f"EmonCMS{id_for_name} {feed_name}"
        else:
            self._attr_name = name
        self._value_template = value_template
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._sensorid = sensorid
        if emoncms_unique_id:
            self._attr_unique_id = f"{emoncms_unique_id}-{elem['id']}"
        else:
            self._attr_unique_id = f"{unique_id}-{elem['id']}"
        if unit_of_measurement in ("kWh", "Wh"):
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif unit_of_measurement == "W":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "V":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "A":
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "VA":
            self._attr_device_class = SensorDeviceClass.APPARENT_POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement in ("°C", "°F", "K"):
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "Hz":
            self._attr_device_class = SensorDeviceClass.FREQUENCY
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif unit_of_measurement == "hPa":
            self._attr_device_class = SensorDeviceClass.PRESSURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._update_attributes(elem)

    def _update_attributes(self, elem: dict[str, Any]) -> None:
        """Update entity attributes."""
        self._attr_extra_state_attributes = {
            ATTR_FEEDID: elem["id"],
            ATTR_TAG: elem["tag"],
            ATTR_FEEDNAME: elem["name"],
        }
        if elem["value"] is not None:
            self._attr_extra_state_attributes[ATTR_SIZE] = elem["size"]
            self._attr_extra_state_attributes[ATTR_USERID] = elem["userid"]
            self._attr_extra_state_attributes[ATTR_LASTUPDATETIME] = elem["time"]
            self._attr_extra_state_attributes[ATTR_LASTUPDATETIMESTR] = (
                template.timestamp_local(float(elem["time"]))
            )

        self._attr_native_value = None
        if self._value_template is not None:
            self._attr_native_value = (
                self._value_template.async_render_with_possible_json_value(
                    elem["value"], STATE_UNKNOWN
                )
            )
        elif elem["value"] is not None:
            self._attr_native_value = round(float(elem["value"]), DECIMALS)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if data:
            self._update_attributes(data[self.idx])
        super()._handle_coordinator_update()
