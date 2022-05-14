"""UniFi Protect Integration services."""
from __future__ import annotations

import asyncio
import functools
from typing import Any, cast

from pydantic import ValidationError
from pyunifiprotect.api import ProtectApiClient
from pyunifiprotect.data import Camera, Chime
from pyunifiprotect.exceptions import BadRequest
import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.service import async_extract_referenced_entity_ids
from homeassistant.util.read_only_dict import ReadOnlyDict

from .const import ATTR_MESSAGE, DOMAIN
from .data import ProtectData
from .utils import _async_unifi_mac_from_hass

SERVICE_ADD_DOORBELL_TEXT = "add_doorbell_text"
SERVICE_REMOVE_DOORBELL_TEXT = "remove_doorbell_text"
SERVICE_SET_DEFAULT_DOORBELL_TEXT = "set_default_doorbell_text"
SERVICE_SET_CHIME_PAIRED = "set_chime_paired_doorbells"

ALL_GLOBAL_SERIVCES = [
    SERVICE_ADD_DOORBELL_TEXT,
    SERVICE_REMOVE_DOORBELL_TEXT,
    SERVICE_SET_DEFAULT_DOORBELL_TEXT,
    SERVICE_SET_CHIME_PAIRED,
]

DOORBELL_TEXT_SCHEMA = vol.All(
    vol.Schema(
        {
            **cv.ENTITY_SERVICE_FIELDS,
            vol.Required(ATTR_MESSAGE): cv.string,
        },
    ),
    cv.has_at_least_one_key(ATTR_DEVICE_ID),
)

CHIME_PAIRED_SCHEMA = vol.All(
    vol.Schema(
        {
            **cv.ENTITY_SERVICE_FIELDS,
            "doorbells": cv.TARGET_SERVICE_FIELDS,
        },
    ),
    cv.has_at_least_one_key(ATTR_ENTITY_ID),
)


def _async_all_ufp_instances(hass: HomeAssistant) -> list[ProtectData]:
    """All active UFP instances."""
    return [
        data for data in hass.data[DOMAIN].values() if isinstance(data, ProtectData)
    ]


@callback
def _async_get_macs_for_device(device_entry: dr.DeviceEntry) -> list[str]:
    return [
        _async_unifi_mac_from_hass(cval)
        for ctype, cval in device_entry.connections
        if ctype == dr.CONNECTION_NETWORK_MAC
    ]


@callback
def _async_get_ufp_instance(
    hass: HomeAssistant, device_id: str
) -> tuple[dr.DeviceEntry, ProtectData]:
    device_registry = dr.async_get(hass)
    if not (device_entry := device_registry.async_get(device_id)):
        raise HomeAssistantError(f"No device found for device id: {device_id}")

    if device_entry.via_device_id is not None:
        return _async_get_ufp_instance(hass, device_entry.via_device_id)

    macs = _async_get_macs_for_device(device_entry)
    ufp_instances = [
        i for i in _async_all_ufp_instances(hass) if i.api.bootstrap.nvr.mac in macs
    ]

    if not ufp_instances:
        # should not be possible unless user manually enters a bad device ID
        raise HomeAssistantError(  # pragma: no cover
            f"No UniFi Protect NVR found for device ID: {device_id}"
        )

    return device_entry, ufp_instances[0]


@callback
def _async_get_protect_from_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[tuple[dr.DeviceEntry, ProtectApiClient]]:
    referenced = async_extract_referenced_entity_ids(hass, call)

    instances: list[tuple[dr.DeviceEntry, ProtectApiClient]] = []
    for device_id in referenced.referenced_devices:
        entry, instance = _async_get_ufp_instance(hass, device_id)
        instances.append((entry, instance.api))

    return instances


async def _async_call_nvr(
    instances: list[tuple[dr.DeviceEntry, ProtectApiClient]],
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    try:
        await asyncio.gather(
            *(getattr(i.bootstrap.nvr, method)(*args, **kwargs) for _, i in instances)
        )
    except (BadRequest, ValidationError) as err:
        raise HomeAssistantError(str(err)) from err


async def add_doorbell_text(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add a custom doorbell text message."""
    message: str = call.data[ATTR_MESSAGE]
    instances = _async_get_protect_from_call(hass, call)
    await _async_call_nvr(instances, "add_custom_doorbell_message", message)


async def remove_doorbell_text(hass: HomeAssistant, call: ServiceCall) -> None:
    """Remove a custom doorbell text message."""
    message: str = call.data[ATTR_MESSAGE]
    instances = _async_get_protect_from_call(hass, call)
    await _async_call_nvr(instances, "remove_custom_doorbell_message", message)


async def set_default_doorbell_text(hass: HomeAssistant, call: ServiceCall) -> None:
    """Set the default doorbell text message."""
    message: str = call.data[ATTR_MESSAGE]
    instances = _async_get_protect_from_call(hass, call)
    await _async_call_nvr(instances, "set_default_doorbell_message", message)


async def set_chime_paired_doorbells(hass: HomeAssistant, call: ServiceCall) -> None:
    """Set paired doorbells on chime."""
    ref = async_extract_referenced_entity_ids(hass, call)
    entity_registry = er.async_get(hass)

    for entity_id in ref.referenced:
        chime_button = entity_registry.async_get(entity_id)
        assert chime_button is not None
        assert chime_button.device_id is not None

        _, instance = _async_get_ufp_instance(hass, chime_button.device_id)
        chime = cast(Chime, instance.async_get_ufp_device(chime_button.unique_id))

        call.data = ReadOnlyDict(call.data.get("doorbells") or {})
        doorbell_refs = async_extract_referenced_entity_ids(hass, call)
        doorbell_ids: set[str] = set()
        for camera_id in doorbell_refs.referenced | doorbell_refs.indirectly_referenced:
            doorbell_sensor = entity_registry.async_get(camera_id)
            assert doorbell_sensor is not None
            if (
                doorbell_sensor.platform != DOMAIN
                or doorbell_sensor.domain != Platform.BINARY_SENSOR
                or doorbell_sensor.original_device_class
                != BinarySensorDeviceClass.OCCUPANCY
            ):
                continue

            camera = cast(
                Camera, instance.async_get_ufp_device(doorbell_sensor.unique_id)
            )
            doorbell_ids.add(camera.id)
        chime.camera_ids = sorted(doorbell_ids)
        await chime.save_device()


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the global UniFi Protect services."""
    services = [
        (
            SERVICE_ADD_DOORBELL_TEXT,
            functools.partial(add_doorbell_text, hass),
            DOORBELL_TEXT_SCHEMA,
        ),
        (
            SERVICE_REMOVE_DOORBELL_TEXT,
            functools.partial(remove_doorbell_text, hass),
            DOORBELL_TEXT_SCHEMA,
        ),
        (
            SERVICE_SET_DEFAULT_DOORBELL_TEXT,
            functools.partial(set_default_doorbell_text, hass),
            DOORBELL_TEXT_SCHEMA,
        ),
        (
            SERVICE_SET_CHIME_PAIRED,
            functools.partial(set_chime_paired_doorbells, hass),
            CHIME_PAIRED_SCHEMA,
        ),
    ]
    for name, method, schema in services:
        if hass.services.has_service(DOMAIN, name):
            continue
        hass.services.async_register(DOMAIN, name, method, schema=schema)


def async_cleanup_services(hass: HomeAssistant) -> None:
    """Cleanup global UniFi Protect services (if all config entries unloaded)."""
    loaded_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state == ConfigEntryState.LOADED
    ]
    if len(loaded_entries) == 1:
        for name in ALL_GLOBAL_SERIVCES:
            hass.services.async_remove(DOMAIN, name)
