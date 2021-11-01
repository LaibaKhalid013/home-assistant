"""NINA sensor platform."""
from typing import Any, Dict, List

from pynina import ApiError, Nina
from pynina import Warning as NinaWarning

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_SAFETY,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    _LOGGER,
    CONF_FILTER_CORONA,
    CONF_MESSAGE_SLOTS,
    CONF_REGIONS,
    DOMAIN,
    SCAN_INTERVAL,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Any
) -> None:
    """Set up entries."""
    config: Dict[str, Any] = hass.data[DOMAIN][config_entry.entry_id]

    regions: Dict[str, str] = config[CONF_REGIONS]

    filter_corona: bool = config[CONF_FILTER_CORONA]

    nina: Nina = Nina()

    for region in regions.keys():
        nina.addRegion(region)

    async def async_update_data():
        """Fetch data from NINA."""
        try:
            await nina.update()

            return nina.warnings

        except ApiError as err:
            _LOGGER.warning("NINA connection error: %s", err)

    coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    entities: List[Message] = []

    for idx, ent in enumerate(coordinator.data):  # pylint: disable=W0612
        for i in range(0, config[CONF_MESSAGE_SLOTS]):
            entities.append(
                Message(coordinator, ent, regions[ent], i + 1, filter_corona)
            )

    async_add_entities(entities)


class Message(CoordinatorEntity, BinarySensorEntity):  # pylint: disable=R0902
    """Representation of an NINA warning."""

    def __init__(  # pylint: disable=R0913
        self,
        coordinator: DataUpdateCoordinator,
        region: str,
        regionName: str,
        slotID: int,
        filter_corona: bool,
    ):
        """Initialize."""
        super().__init__(coordinator)

        self._region: str = region
        self._region_name: str = regionName
        self._has_warning: bool = False
        self._slot_id: int = slotID

        self._message_id: str = ""
        self._message_heading: str = ""
        self._message_sent: str = ""
        self._message_start: str = ""
        self._message_expires: str = ""

        self._filter_corona: bool = filter_corona

        self._coordinator: DataUpdateCoordinator = coordinator

        self.parse_update()

    def parse_update(self):
        """Parse data from coordinator."""
        warnings: List[NinaWarning] = self._coordinator.data[self._region]

        warning_index: int = self._slot_id - 1

        if len(warnings) > warning_index:
            warning: NinaWarning = warnings[warning_index]
            self._message_id = warning.id
            self._message_heading = warning.headline

            self._message_sent = warning.sent or ""
            self._message_start = warning.start or ""
            self._message_expires = warning.expires or ""

            self._has_warning = True

            corona_filter: bool = (
                "corona" in self._message_heading.lower() and self._filter_corona
            )

            if warning.isValid() and not corona_filter:
                return

        self._message_id = ""
        self._message_heading = ""

        self._has_warning = False

        self._message_sent = ""
        self._message_start = ""
        self._message_expires = ""

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Warnung: {self._region_name} {self._slot_id}"

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        self.parse_update()
        return self._has_warning

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes of the sensor."""
        self.parse_update()

        attributes: Dict[str, Any] = {
            "Headline": self._message_heading,
            "ID": self._message_id,
            "Sent": self._message_sent,
            "Start": self._message_start,
            "Expires": self._message_expires,
        }

        return attributes

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{self._region}-{self._slot_id}"

    @property
    def device_class(self) -> str:
        """Return the device class of this entity."""
        return DEVICE_CLASS_SAFETY
