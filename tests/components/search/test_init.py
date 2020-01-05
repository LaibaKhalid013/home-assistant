"""Tests for Search integration."""
from homeassistant.components import search
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_search(hass):
    """Test that search works."""
    area_reg = await hass.helpers.area_registry.async_get_registry()
    device_reg = await hass.helpers.device_registry.async_get_registry()
    entity_reg = await hass.helpers.entity_registry.async_get_registry()

    living_room_area = area_reg.async_create("Living Room")

    # Light strip with 2 lights.
    wled_config_entry = MockConfigEntry(domain="wled")
    wled_config_entry.add_to_hass(hass)

    wled_device = device_reg.async_get_or_create(
        config_entry_id=wled_config_entry.entry_id,
        name="Light Strip",
        identifiers=({"wled", "wled-1"}),
    )

    device_reg.async_update_device(wled_device.id, area_id=living_room_area.id)

    wled_segment_1 = entity_reg.async_get_or_create(
        "light",
        "wled",
        "wled-1-seg-1",
        suggested_object_id="living room light strip segment 1",
        config_entry=wled_config_entry,
        device_id=wled_device.id,
    )
    wled_segment_2 = entity_reg.async_get_or_create(
        "light",
        "wled",
        "wled-1-seg-2",
        suggested_object_id="living room light strip segment 2",
        config_entry=wled_config_entry,
        device_id=wled_device.id,
    )

    # Non related info.
    kitchen_area = area_reg.async_create("Kitchen")

    hue_config_entry = MockConfigEntry(domain="hue")
    hue_config_entry.add_to_hass(hass)

    hue_device = device_reg.async_get_or_create(
        config_entry_id=hue_config_entry.entry_id,
        name="Light Strip",
        identifiers=({"hue", "hue-1"}),
    )

    device_reg.async_update_device(hue_device.id, area_id=kitchen_area.id)

    entity_reg.async_get_or_create(
        "light",
        "hue",
        "hue-1-seg-1",
        suggested_object_id="living room light strip segment 1",
        config_entry=hue_config_entry,
        device_id=hue_device.id,
    )
    entity_reg.async_get_or_create(
        "light",
        "hue",
        "hue-1-seg-2",
        suggested_object_id="living room light strip segment 2",
        config_entry=hue_config_entry,
        device_id=hue_device.id,
    )

    expected = {
        "area": {living_room_area.id},
        "device": {wled_device.id},
        "entity": {wled_segment_1.entity_id, wled_segment_2.entity_id},
    }

    # Explore the graph from every node and make sure we find the same results
    for search_type, search_id in (
        ("area", living_room_area.id),
        ("device", wled_device.id),
        ("entity", wled_segment_1.entity_id),
        ("entity", wled_segment_2.entity_id),
    ):
        searcher = search.Searcher(hass, device_reg, entity_reg)
        results = await searcher.search(search_type, search_id)
        # Add the item we searched for, it's omitted from results
        results.setdefault(search_type, set()).add(search_id)
        assert (
            results == expected
        ), f"Results for {search_type}/{search_id} do not match up"


async def test_ws_api(hass, hass_ws_client):
    """Test WS API."""
    assert await async_setup_component(hass, "search", {})

    area_reg = await hass.helpers.area_registry.async_get_registry()
    device_reg = await hass.helpers.device_registry.async_get_registry()

    kitchen_area = area_reg.async_create("Kitchen")

    hue_config_entry = MockConfigEntry(domain="hue")
    hue_config_entry.add_to_hass(hass)

    hue_device = device_reg.async_get_or_create(
        config_entry_id=hue_config_entry.entry_id,
        name="Light Strip",
        identifiers=({"hue", "hue-1"}),
    )

    device_reg.async_update_device(hue_device.id, area_id=kitchen_area.id)

    client = await hass_ws_client(hass)

    await client.send_json(
        {"id": 1, "type": "search", "item_type": "device", "item_id": hue_device.id}
    )
    response = await client.receive_json()
    assert response["success"]
    assert response["result"] == {"area": [kitchen_area.id]}
