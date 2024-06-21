"""Test Enphase Envoy diagnostics."""

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.enphase_envoy.const import Platform
from homeassistant.components.number import SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry

NUMBER_FIXTURES = (
    [
        pytest.param("envoy_metered_batt_relay", 7, id="envoy_metered_batt_relay"),
    ],
)


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *NUMBER_FIXTURES, indirect=["mock_envoy"]
)
async def test_number(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    entity_registry: er.EntityRegistry,
    entity_count: int,
) -> None:
    """Test enphase_envoy number entities."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.NUMBER])

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
    ("mock_envoy", "entity_count"), *NUMBER_FIXTURES, indirect=["mock_envoy"]
)
async def test_number_operation(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    mock_set_reserve_soc: AsyncMock,
    entity_count: int,
) -> None:
    """Test enphase_envoy number entities operation."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.NUMBER])
    assert len(hass.states.async_all()) == entity_count

    entity_base = f"{Platform.NUMBER}.enpower_"

    sn = mock_envoy.data.enpower.serial_number
    test_entity = f"{entity_base}{sn}_reserve_battery_level"
    assert (entity_state := hass.states.get(test_entity))
    assert mock_envoy.data.tariff.storage_settings.reserved_soc == float(
        entity_state.state
    )
    test_value = 2 * float(entity_state.state)
    await hass.services.async_call(
        Platform.NUMBER,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: test_entity,
            "value": test_value,
        },
        blocking=True,
    )

    mock_set_reserve_soc.assert_awaited_once()
    mock_set_reserve_soc.assert_called_with(test_value)
    mock_set_reserve_soc.reset_mock()
