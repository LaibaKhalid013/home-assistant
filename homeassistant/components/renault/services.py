"""Support for Renault services."""
from __future__ import annotations

from datetime import datetime
import logging
from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .renault_hub import RenaultHub
from .renault_vehicle import RenaultVehicleProxy

LOGGER = logging.getLogger(__name__)

ATTR_CHARGE_MODE = "charge_mode"
ATTR_SCHEDULES = "schedules"
ATTR_TEMPERATURE = "temperature"
ATTR_VIN = "vin"
ATTR_WHEN = "when"

REGEX_VIN = "(?i)^VF1[\\w]{14}$"

SERVICE_AC_CANCEL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VIN): cv.matches_regex(REGEX_VIN),
    }
)
SERVICE_AC_START_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(ATTR_TEMPERATURE): cv.positive_float,
        vol.Optional(ATTR_WHEN): cv.datetime,
    }
)
SERVICE_CHARGE_SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(ATTR_CHARGE_MODE): vol.In(
            ["always", "always_charging", "schedule_mode"]
        ),
    }
)
SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA = vol.Schema(
    {
        vol.Required("startTime"): cv.string,
        vol.Required("duration"): cv.positive_int,
    }
)
SERVICE_CHARGE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): cv.positive_int,
        vol.Optional("activated"): cv.boolean,
        vol.Optional("monday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("tuesday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("wednesday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("thursday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("friday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("saturday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("sunday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
    }
)
SERVICE_CHARGE_SET_SCHEDULES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(ATTR_SCHEDULES): vol.All(
            cv.ensure_list, [SERVICE_CHARGE_SET_SCHEDULE_SCHEMA]
        ),
    }
)
SERVICE_CHARGE_START_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VIN): cv.matches_regex(REGEX_VIN),
    }
)

SERVICE_AC_CANCEL = "ac_cancel"
SERVICE_AC_START = "ac_start"
SERVICE_CHARGE_SET_MODE = "charge_set_mode"
SERVICE_CHARGE_SET_SCHEDULES = "charge_set_schedules"
SERVICE_CHARGE_START = "charge_start"
SERVICES = [
    SERVICE_AC_CANCEL,
    SERVICE_AC_START,
    SERVICE_CHARGE_SET_MODE,
    SERVICE_CHARGE_SET_SCHEDULES,
    SERVICE_CHARGE_START,
]


def setup_services(hass: HomeAssistant) -> None:
    """Register the Renault services."""

    async def ac_cancel(service_call: ServiceCall) -> None:
        """Cancel A/C."""
        proxy = get_vehicle_proxy(service_call.data)

        LOGGER.debug("A/C cancel attempt")
        result = await proxy._vehicle.set_ac_stop()
        LOGGER.info("A/C cancel result: %s", result)

    async def ac_start(service_call: ServiceCall) -> None:
        """Start A/C."""
        temperature: float = service_call.data[ATTR_TEMPERATURE]
        when: datetime | None = service_call.data.get(ATTR_WHEN)
        proxy = get_vehicle_proxy(service_call.data)

        LOGGER.debug("A/C start attempt: %s / %s", temperature, when)
        result = await proxy._vehicle.set_ac_start(temperature, when)
        LOGGER.info("A/C start result: %s", result.raw_data)

    async def charge_set_mode(service_call: ServiceCall) -> None:
        """Set charge mode."""
        charge_mode: str = service_call.data[ATTR_CHARGE_MODE]
        proxy = get_vehicle_proxy(service_call.data)

        LOGGER.debug("Charge set mode attempt: %s", charge_mode)
        result = await proxy._vehicle.set_charge_mode(charge_mode)
        LOGGER.info("Charge set mode result: %s", result)

    async def charge_set_schedules(service_call: ServiceCall) -> None:
        """Set charge schedules."""
        schedules: list[dict[str, Any]] = service_call.data[ATTR_SCHEDULES]
        proxy = get_vehicle_proxy(service_call.data)
        charge_schedules = await proxy._vehicle.get_charging_settings()
        for schedule in schedules:
            charge_schedules.update(schedule)

        assert charge_schedules.schedules is not None
        LOGGER.debug("Charge set schedules attempt: %s", schedules)
        result = await proxy._vehicle.set_charge_schedules(charge_schedules.schedules)
        LOGGER.info("Charge set schedules result: %s", result)
        LOGGER.info(
            "It may take some time before these changes are reflected in your vehicle"
        )

    async def charge_start(service_call: ServiceCall) -> None:
        """Start charge."""
        proxy = get_vehicle_proxy(service_call.data)

        LOGGER.debug("Charge start attempt")
        result = await proxy._vehicle.set_charge_start()
        LOGGER.info("Charge start result: %s", result)

    def get_vehicle_proxy(service_call_data: MappingProxyType) -> RenaultVehicleProxy:
        """Get vehicle from service_call data."""
        vin: str = service_call_data[ATTR_VIN]
        proxy: RenaultHub
        for proxy in hass.data[DOMAIN].values():
            vehicle = proxy.vehicles.get(vin)
            if vehicle is not None:
                return vehicle
        raise ValueError(f"Unable to find vehicle with VIN: {vin}")

    hass.services.async_register(
        DOMAIN,
        SERVICE_AC_CANCEL,
        ac_cancel,
        schema=SERVICE_AC_CANCEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_AC_START,
        ac_start,
        schema=SERVICE_AC_START_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_SET_MODE,
        charge_set_mode,
        schema=SERVICE_CHARGE_SET_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_SET_SCHEDULES,
        charge_set_schedules,
        schema=SERVICE_CHARGE_SET_SCHEDULES_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_START,
        charge_start,
        schema=SERVICE_CHARGE_START_SCHEMA,
    )


def unload_services(hass: HomeAssistant) -> None:
    """Unload Renault services."""
    for service in SERVICES:
        hass.services.async_remove(DOMAIN, service)
