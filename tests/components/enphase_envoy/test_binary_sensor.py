"""Test Enphase Envoy binary sensors."""

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.enphase_envoy.const import Platform
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry

BINARY_FIXTURES = (
    [
        pytest.param("envoy_metered_batt_relay", 4, id="envoy_metered_batt_relay"),
    ],
)


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *BINARY_FIXTURES, indirect=["mock_envoy"]
)
async def test_binary_sensor(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    entity_registry: er.EntityRegistry,
    entity_count: int,
) -> None:
    """Test enphase_envoy binary_sensor entities."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.BINARY_SENSOR])

    # number entities states should be created from test data
    assert len(hass.states.async_all()) == entity_count

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    assert len(entity_entries) == entity_count

    # compare registered entities against snapshot of prior run
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert hass.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *BINARY_FIXTURES, indirect=["mock_envoy"]
)
async def test_binary_sensor_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: er.EntityRegistry,
    entity_count: int,
) -> None:
    """Test enphase_envoy encharge enpower entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.BINARY_SENSOR])
    assert len(hass.states.async_all()) == entity_count

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.BINARY_SENSOR}.enpower_"

    sn = mock_envoy.data.enpower.serial_number
    assert (entity_state := hass.states.get(f"{entity_base}{sn}_communicating"))
    assert (
        entity_state.state == STATE_ON
        if mock_envoy.data.enpower.communicating
        else STATE_OFF
    )
    assert (entity_state := hass.states.get(f"{entity_base}{sn}_grid_status"))
    assert (
        entity_state.state == STATE_ON
        if mock_envoy.data.enpower.mains_oper_state == "closed"
        else STATE_OFF
    )

    entity_base = "binary_sensor.encharge_"

    # these should be defined and have value from data
    for sn, encharge_inventory in mock_envoy.data.encharge_inventory.items():
        assert (entity_state := hass.states.get(f"{entity_base}{sn}_communicating"))
        assert (
            entity_state.state == STATE_ON
            if encharge_inventory.communicating
            else STATE_OFF
        )
        assert (entity_state := hass.states.get(f"{entity_base}{sn}_dc_switch"))
        assert (
            entity_state.state == STATE_ON
            if encharge_inventory.dc_switch_off
            else STATE_OFF
        )
