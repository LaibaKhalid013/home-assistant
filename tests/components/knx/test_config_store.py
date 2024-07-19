"""Test KNX devices."""

from typing import Any

import pytest

from homeassistant.components.knx.storage.config_store import (
    STORAGE_KEY as KNX_CONFIG_STORAGE_KEY,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import KNXTestKit

from tests.typing import MockHAClientWebSocket, WebSocketGenerator


async def _create_test_switch(
    entity_registry: er.EntityRegistry,
    ws_client: MockHAClientWebSocket,
) -> er.RegistryEntry:
    """Create a test switch entity and return its entity_id and name."""
    test_name = "Test no device"
    test_entity_id = "switch.test_no_device"
    assert not entity_registry.async_get(test_entity_id)

    await ws_client.send_json_auto_id(
        {
            "type": "knx/create_entity",
            "platform": Platform.SWITCH,
            "data": {
                "entity": {"name": test_name},
                "knx": {"ga_switch": {"write": "1/2/3"}},
            },
        }
    )
    res = await ws_client.receive_json()
    assert res["success"], res
    assert res["result"]["success"] is True
    assert res["result"]["entity_id"] == test_entity_id

    entity = entity_registry.async_get(test_entity_id)
    assert entity
    return entity


async def test_create_switch(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity creation."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    test_entity = await _create_test_switch(entity_registry, client)

    # Test if entity is correctly stored in registry
    await client.send_json_auto_id({"type": "knx/get_entity_entries"})
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"] == [
        test_entity.extended_dict,
    ]
    # Test if entity is correctly stored in config store
    await client.send_json_auto_id(
        {
            "type": "knx/get_entity_config",
            "entity_id": test_entity.entity_id,
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"] == {
        "platform": Platform.SWITCH,
        "unique_id": test_entity.unique_id,
        "data": {
            "entity": {
                "name": test_entity.original_name,
                "device_info": None,
                "entity_category": None,
            },
            "knx": {
                "ga_switch": {"write": "1/2/3", "state": None, "passive": []},
                "invert": False,
                "respond_to_read": False,
                "sync_state": True,
            },
        },
        "schema_options": None,
    }


async def test_create_entity_error(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test unsuccessful entity creation."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    # create entity with invalid platform
    await client.send_json_auto_id(
        {
            "type": "knx/create_entity",
            "platform": "invalid_platform",
            "data": {
                "entity": {"name": "Test invalid platform"},
                "knx": {"ga_switch": {"write": "1/2/3"}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert not res["result"]["success"]
    assert res["result"]["errors"][0]["path"] == ["platform"]
    assert res["result"]["error_base"].startswith("expected Platform or one of")

    # create entity with unsupported platform
    await client.send_json_auto_id(
        {
            "type": "knx/create_entity",
            "platform": Platform.TTS,  # "tts" is not a supported platform (and is unlikely te ever be)
            "data": {
                "entity": {"name": "Test invalid platform"},
                "knx": {"ga_switch": {"write": "1/2/3"}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert not res["result"]["success"]
    assert res["result"]["errors"][0]["path"] == ["platform"]
    assert res["result"]["error_base"].startswith("value must be one of")


async def test_update_entity(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity update."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    test_entity = await _create_test_switch(entity_registry, client)
    test_entity_id = test_entity.entity_id

    # update entity
    new_name = "Updated name"
    new_ga_switch_write = "4/5/6"
    await client.send_json_auto_id(
        {
            "type": "knx/update_entity",
            "platform": Platform.SWITCH,
            "unique_id": test_entity.unique_id,
            "data": {
                "entity": {"name": new_name},
                "knx": {"ga_switch": {"write": new_ga_switch_write}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["success"]

    entity = entity_registry.async_get(test_entity_id)
    assert entity
    assert entity.original_name == new_name

    assert (
        hass_storage[KNX_CONFIG_STORAGE_KEY]["data"]["entities"]["switch"][
            test_entity.unique_id
        ]["knx"]["ga_switch"]["write"]
        == new_ga_switch_write
    )


async def test_update_entity_error(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity update."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    test_entity = await _create_test_switch(entity_registry, client)

    # update unsupported platform
    new_name = "Updated name"
    new_ga_switch_write = "4/5/6"
    await client.send_json_auto_id(
        {
            "type": "knx/update_entity",
            "platform": Platform.TTS,
            "unique_id": test_entity.unique_id,
            "data": {
                "entity": {"name": new_name},
                "knx": {"ga_switch": {"write": new_ga_switch_write}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert not res["result"]["success"]
    assert res["result"]["errors"][0]["path"] == ["platform"]
    assert res["result"]["error_base"].startswith("value must be one of")

    # entity not found
    await client.send_json_auto_id(
        {
            "type": "knx/update_entity",
            "platform": Platform.SWITCH,
            "unique_id": "non_existing_unique_id",
            "data": {
                "entity": {"name": new_name},
                "knx": {"ga_switch": {"write": new_ga_switch_write}},
            },
        }
    )
    res = await client.receive_json()
    assert not res["success"], res
    assert res["error"]["code"] == "home_assistant_error"
    assert res["error"]["message"].startswith("Entity not found in")


async def test_delete_entity(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity deletion."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    test_entity = await _create_test_switch(entity_registry, client)
    test_entity_id = test_entity.entity_id

    # delete entity
    await client.send_json_auto_id(
        {
            "type": "knx/delete_entity",
            "entity_id": test_entity_id,
        }
    )
    res = await client.receive_json()
    assert res["success"], res

    assert not entity_registry.async_get(test_entity_id)
    assert not hass_storage[KNX_CONFIG_STORAGE_KEY]["data"]["entities"].get("switch")


async def test_delete_entity_error(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test unsuccessful entity deletion."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    # delete unknown entity
    await client.send_json_auto_id(
        {
            "type": "knx/delete_entity",
            "entity_id": "switch.non_existing_entity",
        }
    )
    res = await client.receive_json()
    assert not res["success"], res
    assert res["error"]["code"] == "home_assistant_error"
    assert res["error"]["message"].startswith("Entity not found")

    # delete entity not in config store
    test_entity_id = "sensor.knx_interface_individual_address"
    assert entity_registry.async_get(test_entity_id)
    await client.send_json_auto_id(
        {
            "type": "knx/delete_entity",
            "entity_id": test_entity_id,
        }
    )
    res = await client.receive_json()
    assert not res["success"], res
    assert res["error"]["code"] == "home_assistant_error"
    assert res["error"]["message"].startswith("Entity not found")


async def test_get_entity_config(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity config retrieval."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    test_entity = await _create_test_switch(entity_registry, client)

    await client.send_json_auto_id(
        {
            "type": "knx/get_entity_config",
            "entity_id": test_entity.entity_id,
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["platform"] == Platform.SWITCH
    assert res["result"]["unique_id"] == test_entity.unique_id
    assert res["result"]["data"] == {
        "entity": {
            "name": "Test no device",
            "device_info": None,
            "entity_category": None,
        },
        "knx": {
            "ga_switch": {"write": "1/2/3", "passive": [], "state": None},
            "respond_to_read": False,
            "invert": False,
            "sync_state": True,
        },
    }


@pytest.mark.parametrize(
    ("test_entity_id", "error_message_start"),
    [
        ("switch.non_existing_entity", "Entity not found"),
        ("sensor.knx_interface_individual_address", "Entity data not found"),
    ],
)
async def test_get_entity_config_error(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    test_entity_id: str,
    error_message_start: str,
) -> None:
    """Test entity config retrieval errors."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "knx/get_entity_config",
            "entity_id": test_entity_id,
        }
    )
    res = await client.receive_json()
    assert not res["success"], res
    assert res["error"]["code"] == "home_assistant_error"
    assert res["error"]["message"].startswith(error_message_start)


async def test_validate_entity(
    hass: HomeAssistant,
    knx: KNXTestKit,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Test entity validation."""
    await knx.setup_integration({})
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "knx/validate_entity",
            "platform": Platform.SWITCH,
            "data": {
                "entity": {"name": "test_name"},
                "knx": {"ga_switch": {"write": "1/2/3"}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["success"] is True

    # invalid data
    await client.send_json_auto_id(
        {
            "type": "knx/validate_entity",
            "platform": Platform.SWITCH,
            "data": {
                "entity": {"name": "test_name"},
                "knx": {"ga_switch": {}},
            },
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["success"] is False
    assert res["result"]["errors"][0]["path"] == ["data", "knx", "ga_switch", "write"]
    assert res["result"]["errors"][0]["error_message"] == "required key not provided"
    assert res["result"]["error_base"].startswith("required key not provided")
