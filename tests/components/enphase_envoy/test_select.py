"""Test Enphase Envoy diagnostics."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.enphase_envoy.const import Platform
from homeassistant.components.enphase_envoy.select import (
    ACTION_OPTIONS,
    MODE_OPTIONS,
    RELAY_ACTION_MAP,
    RELAY_MODE_MAP,
    REVERSE_RELAY_ACTION_MAP,
    REVERSE_RELAY_MODE_MAP,
    REVERSE_STORAGE_MODE_MAP,
    STORAGE_MODE_MAP,
    STORAGE_MODE_OPTIONS,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry

SELECT_STORAGE_FIXTURES = (
    [
        pytest.param("envoy_metered_batt_relay", 13, id="envoy_metered_batt_relay"),
    ],
)
SELECT_FIXTURES = (
    [
        pytest.param("envoy", 0, id="envoy"),
        pytest.param("envoy_metered_batt_relay", 13, id="envoy_metered_batt_relay"),
        pytest.param("envoy_nobatt_metered_3p", 0, id="envoy_nobatt_metered_3p"),
        pytest.param("envoy_1p_metered", 0, id="envoy_1p_metered"),
        pytest.param("envoy_tot_cons_metered", 0, id="envoy_tot_cons_metered"),
    ],
)


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *SELECT_FIXTURES, indirect=["mock_envoy"]
)
async def test_select(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    entity_registry: er.EntityRegistry,
    entity_count: int,
) -> None:
    """Test enphase_envoy select entities."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SELECT])

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
    ("mock_envoy", "entity_count"), *SELECT_FIXTURES, indirect=["mock_envoy"]
)
async def test_select_relay_actions(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    mock_update_dry_contact: AsyncMock,
    entity_count: int,
) -> None:
    """Test enphase_envoy select relay entities actions."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SELECT])
    assert len(hass.states.async_all()) == entity_count

    entity_base = f"{Platform.SELECT}."

    for contact_id, dry_contact in mock_envoy.data.dry_contact_settings.items():
        name = dry_contact.load_name.lower().replace(" ", "_")
        targets: list[Any] = []
        targets.extend(
            (
                ("generator_action", dry_contact.generator_action),
                ("microgrid_action", dry_contact.micro_grid_action),
                ("grid_action", dry_contact.grid_action),
            )
        )
        for target in targets:
            test_entity = f"{entity_base}{name}_{target[0]}"
            assert (entity_state := hass.states.get(test_entity))
            assert RELAY_ACTION_MAP[target[1]] == (current_state := entity_state.state)
            for mode in [mode for mode in ACTION_OPTIONS if not current_state]:
                await hass.services.async_call(
                    Platform.SELECT,
                    "select_option",
                    {
                        ATTR_ENTITY_ID: test_entity,
                        "option": mode,
                    },
                    blocking=True,
                )
                mock_update_dry_contact.assert_awaited_once()
                mock_update_dry_contact.assert_called_with(
                    {"id": contact_id, target[0]: REVERSE_RELAY_ACTION_MAP[mode]}
                )
                mock_update_dry_contact.reset_mock()


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *SELECT_FIXTURES, indirect=["mock_envoy"]
)
async def test_select_relay_modes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    mock_update_dry_contact: AsyncMock,
    entity_count: int,
) -> None:
    """Test enphase_envoy select relay entities modes."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SELECT])
    assert len(hass.states.async_all()) == entity_count

    entity_base = f"{Platform.SELECT}."

    for contact_id, dry_contact in mock_envoy.data.dry_contact_settings.items():
        name = dry_contact.load_name.lower().replace(" ", "_")
        test_entity = f"{entity_base}{name}_mode"
        assert (entity_state := hass.states.get(test_entity))
        assert RELAY_MODE_MAP[dry_contact.mode] == (current_state := entity_state.state)
        for mode in [mode for mode in MODE_OPTIONS if not current_state]:
            await hass.services.async_call(
                Platform.SELECT,
                "select_option",
                {
                    ATTR_ENTITY_ID: test_entity,
                    "option": mode,
                },
                blocking=True,
            )
            mock_update_dry_contact.assert_awaited_once()
            mock_update_dry_contact.assert_called_with(
                {"id": contact_id, "mode": REVERSE_RELAY_MODE_MAP[mode]}
            )
            mock_update_dry_contact.reset_mock()


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count"), *SELECT_STORAGE_FIXTURES, indirect=["mock_envoy"]
)
async def test_select_storage_modes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    mock_set_storage_mode: AsyncMock,
    entity_count: int,
) -> None:
    """Test enphase_envoy select entities storage modes."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SELECT])
    assert len(hass.states.async_all()) == entity_count

    entity_base = f"{Platform.SELECT}.enpower_"

    sn = mock_envoy.data.enpower.serial_number
    test_entity = f"{entity_base}{sn}_storage_mode"
    assert (entity_state := hass.states.get(test_entity))
    assert STORAGE_MODE_MAP[mock_envoy.data.tariff.storage_settings.mode] == (
        current_state := entity_state.state
    )

    for mode in [mode for mode in STORAGE_MODE_OPTIONS if not current_state]:
        await hass.services.async_call(
            Platform.SELECT,
            "select_option",
            {
                ATTR_ENTITY_ID: test_entity,
                "option": mode,
            },
            blocking=True,
        )
        mock_set_storage_mode.assert_awaited_once()
        mock_set_storage_mode.assert_called_with(REVERSE_STORAGE_MODE_MAP[mode])
        mock_set_storage_mode.reset_mock()
