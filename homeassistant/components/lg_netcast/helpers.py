"""Helper functions for LG Netcast TV."""
from functools import partial
from typing import TypedDict

import defusedxml.ElementTree as DET
from pylgnetcast import LgNetCastClient
from requests import RequestException

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN


class LGNetCastDetailDiscoveryError(Exception):
    """Unable to retrieve details from Netcast TV."""


class NetcastDetails(TypedDict):
    """Netcast TV Details."""

    uuid: str
    model_name: str
    friendly_name: str


async def async_discover_netcast_details(
    hass: HomeAssistant, client: LgNetCastClient
) -> NetcastDetails:
    """Discover UUID and Model Name from Netcast Tv."""
    # We're using UDAP to retrieve this information, which requires a specific User-Agent
    client.HEADER = {**LgNetCastClient.HEADER, "User-Agent": "UDAP/2.0"}

    try:
        resp = await hass.async_add_executor_job(
            partial(client._send_to_tv, payload={"target": "rootservice.xml"}),  # pylint: disable=protected-access
            "data",
        )
    except RequestException as err:
        raise LGNetCastDetailDiscoveryError(
            f"Error in connecting to {client.url}"
        ) from err

    if resp.status_code != 200:
        raise LGNetCastDetailDiscoveryError(
            "Invalid response ({resp.status_code}) from: {resp.url}"
        )

    try:
        tree = DET.fromstring(resp.text.encode("utf-8"))
    except DET.ParseError as err:
        raise LGNetCastDetailDiscoveryError("Invalid XML") from err

    return {
        "uuid": tree.findtext("device/uuid"),
        "model_name": tree.findtext("device/modelName"),
        "friendly_name": tree.findtext("device/friendlyName"),
    }


@callback
def async_get_device_entry_by_device_id(
    hass: HomeAssistant, device_id: str
) -> DeviceEntry:
    """Get Device Entry from Device Registry by device ID.

    Raises ValueError if device ID is invalid.
    """
    device_reg = dr.async_get(hass)
    if (device := device_reg.async_get(device_id)) is None:
        raise ValueError(f"Device {device_id} is not a valid {DOMAIN} device.")

    return device


@callback
def async_get_client_by_device_entry(
    hass: HomeAssistant, device: DeviceEntry
) -> LgNetCastClient:
    """Get LG Netcast from Device Registry by device entry.

    Raises ValueError if client is not found.
    """
    for config_entry_id in device.config_entries:
        if client := hass.data[DOMAIN].get(config_entry_id):
            return client

    raise ValueError(
        f"Device {device.id} is not from an existing {DOMAIN} config entry"
    )


@callback
def async_get_device_id_from_entity_id(hass: HomeAssistant, entity_id: str) -> str:
    """Get a device ID from an entity ID.

    Raises ValueError is entity or device ID is invalid.
    """
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)

    if (
        entity_entry is None
        or entity_entry.device_id is None
        or entity_entry.platform != DOMAIN
    ):
        raise ValueError(f"Entity {entity_id} is not a valid {DOMAIN} entity.")

    return entity_entry.device_id
