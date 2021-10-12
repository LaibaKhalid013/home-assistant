"""Support for RainMachine devices."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial
from typing import Any

from regenmaschine import Client
from regenmaschine.controller import Controller
from regenmaschine.errors import RainMachineError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client, config_validation as cv
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util.network import is_ip_address

from .config_flow import get_client_controller
from .const import (
    CONF_ZONE_RUN_TIME,
    DATA_CONTROLLER,
    DATA_COORDINATOR,
    DATA_PROGRAMS,
    DATA_PROVISION_SETTINGS,
    DATA_RESTRICTIONS_CURRENT,
    DATA_RESTRICTIONS_UNIVERSAL,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
)

CONF_SECONDS = "seconds"

DEFAULT_ATTRIBUTION = "Data provided by Green Electronics LLC"
DEFAULT_ICON = "mdi:water"
DEFAULT_SSL = True
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=15)

CONFIG_SCHEMA = cv.deprecated(DOMAIN)

PLATFORMS = ["binary_sensor", "sensor", "switch"]

SERVICE_NAME_PAUSE_WATERING = "pause_watering"
SERVICE_NAME_STOP_ALL = "stop_all"
SERVICE_NAME_UNPAUSE_WATERING = "unpause_watering"

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)

SERVICE_PAUSE_WATERING_SCHEMA = SERVICE_SCHEMA.extend(
    {
        vol.Required(CONF_SECONDS): cv.positive_int,
    }
)


@callback
def async_get_controller_for_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> Controller:
    """Get the controller related to a service call (by device ID)."""
    controllers: dict[str, Controller] = hass.data[DOMAIN][DATA_CONTROLLER]
    device_id = call.data[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)

    if device_entry := device_registry.async_get(device_id):
        for entry_id in device_entry.config_entries:
            if entry_id in controllers:
                return controllers[entry_id]

    raise ValueError(f"No controller for device ID: {device_id}")


async def async_update_programs_and_zones(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Update program and zone DataUpdateCoordinators.

    Program and zone updates always go together because of how linked they are:
    programs affect zones and certain combinations of zones affect programs.
    """
    await asyncio.gather(
        *[
            hass.data[DOMAIN][DATA_COORDINATOR][entry.entry_id][
                DATA_PROGRAMS
            ].async_refresh(),
            hass.data[DOMAIN][DATA_COORDINATOR][entry.entry_id][
                DATA_ZONES
            ].async_refresh(),
        ]
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RainMachine as config entry."""
    hass.data.setdefault(DOMAIN, {DATA_CONTROLLER: {}, DATA_COORDINATOR: {}})
    hass.data[DOMAIN][DATA_COORDINATOR][entry.entry_id] = {}
    websession = aiohttp_client.async_get_clientsession(hass)
    client = Client(session=websession)

    try:
        await client.load_local(
            entry.data[CONF_IP_ADDRESS],
            entry.data[CONF_PASSWORD],
            port=entry.data[CONF_PORT],
            ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        )
    except RainMachineError as err:
        raise ConfigEntryNotReady from err

    # regenmaschine can load multiple controllers at once, but we only grab the one
    # we loaded above:
    controller = hass.data[DOMAIN][DATA_CONTROLLER][
        entry.entry_id
    ] = get_client_controller(client)

    entry_updates: dict[str, Any] = {}
    if not entry.unique_id or is_ip_address(entry.unique_id):
        # If the config entry doesn't already have a unique ID, set one:
        entry_updates["unique_id"] = controller.mac
    if CONF_ZONE_RUN_TIME in entry.data:
        # If a zone run time exists in the config entry's data, pop it and move it to
        # options:
        data = {**entry.data}
        entry_updates["data"] = data
        entry_updates["options"] = {
            **entry.options,
            CONF_ZONE_RUN_TIME: data.pop(CONF_ZONE_RUN_TIME),
        }
    if entry_updates:
        hass.config_entries.async_update_entry(entry, **entry_updates)

    async def async_update(api_category: str) -> dict:
        """Update the appropriate API data based on a category."""
        data: dict = {}

        try:
            if api_category == DATA_PROGRAMS:
                data = await controller.programs.all(include_inactive=True)
            elif api_category == DATA_PROVISION_SETTINGS:
                data = await controller.provisioning.settings()
            elif api_category == DATA_RESTRICTIONS_CURRENT:
                data = await controller.restrictions.current()
            elif api_category == DATA_RESTRICTIONS_UNIVERSAL:
                data = await controller.restrictions.universal()
            else:
                data = await controller.zones.all(details=True, include_inactive=True)
        except RainMachineError as err:
            raise UpdateFailed(err) from err

        return data

    controller_init_tasks = []
    for api_category in (
        DATA_PROGRAMS,
        DATA_PROVISION_SETTINGS,
        DATA_RESTRICTIONS_CURRENT,
        DATA_RESTRICTIONS_UNIVERSAL,
        DATA_ZONES,
    ):
        coordinator = hass.data[DOMAIN][DATA_COORDINATOR][entry.entry_id][
            api_category
        ] = DataUpdateCoordinator(
            hass,
            LOGGER,
            name=f'{controller.name} ("{api_category}")',
            update_interval=DEFAULT_UPDATE_INTERVAL,
            update_method=partial(async_update, api_category),
        )
        controller_init_tasks.append(coordinator.async_refresh())

    await asyncio.gather(*controller_init_tasks)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def async_pause_watering(call: ServiceCall) -> None:
        """Pause watering for a set number of seconds."""
        controller = async_get_controller_for_service_call(hass, call)
        await controller.watering.pause_all(call.data[CONF_SECONDS])
        await async_update_programs_and_zones(hass, entry)

    async def async_stop_all(call: ServiceCall) -> None:
        """Stop all watering."""
        controller = async_get_controller_for_service_call(hass, call)
        await controller.watering.stop_all()
        await async_update_programs_and_zones(hass, entry)

    async def async_unpause_watering(call: ServiceCall) -> None:
        """Unpause watering."""
        controller = async_get_controller_for_service_call(hass, call)
        await controller.watering.unpause_all()
        await async_update_programs_and_zones(hass, entry)

    for service_name, schema, method in (
        (
            SERVICE_NAME_PAUSE_WATERING,
            SERVICE_PAUSE_WATERING_SCHEMA,
            async_pause_watering,
        ),
        (SERVICE_NAME_STOP_ALL, SERVICE_SCHEMA, async_stop_all),
        (SERVICE_NAME_UNPAUSE_WATERING, SERVICE_SCHEMA, async_unpause_watering),
    ):
        if hass.services.has_service(DOMAIN, service_name):
            continue
        hass.services.async_register(DOMAIN, service_name, method, schema=schema)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an RainMachine config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN][DATA_COORDINATOR].pop(entry.entry_id)

    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        # If this is the last instance of RainMachine, deregister any services defined
        # during integration setup:
        for service_name in (
            SERVICE_NAME_PAUSE_WATERING,
            SERVICE_NAME_STOP_ALL,
            SERVICE_NAME_UNPAUSE_WATERING,
        ):
            hass.services.async_remove(DOMAIN, service_name)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class RainMachineEntity(CoordinatorEntity):
    """Define a generic RainMachine entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        controller: Controller,
        description: EntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_device_info = {
            "identifiers": {(DOMAIN, controller.mac)},
            "connections": {(dr.CONNECTION_NETWORK_MAC, controller.mac)},
            "name": str(controller.name),
            "manufacturer": "RainMachine",
            "model": (
                f"Version {controller.hardware_version} "
                f"(API: {controller.api_version})"
            ),
            "sw_version": controller.software_version,
        }
        self._attr_extra_state_attributes = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        # The colons are removed from the device MAC simply because that value
        # (unnecessarily) makes up the existing unique ID formula and we want to avoid
        # a breaking change:
        self._attr_unique_id = f"{controller.mac.replace(':', '')}_{description.key}"
        self._controller = controller
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        self.update_from_latest_data()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.update_from_latest_data()

    @callback
    def update_from_latest_data(self) -> None:
        """Update the state."""
        raise NotImplementedError
