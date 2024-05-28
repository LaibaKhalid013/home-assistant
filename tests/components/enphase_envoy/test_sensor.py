"""Test Enphase Envoy sensors."""

import itertools
from unittest.mock import AsyncMock

from pyenphase.const import PHASENAMES
from pyenphase.models.meters import CtType
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.enphase_envoy.const import Platform
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from tests.common import MockConfigEntry
from tests.components.enphase_envoy import setup_with_selected_platforms

SENSOR_FIXTURES = (
    [
        pytest.param("envoy", 5, 6, id="envoy"),
        pytest.param(
            "envoy_metered_batt_relay", 27, 106, id="envoy_metered_batt_relay"
        ),
        pytest.param("envoy_nobatt_metered_3p", 12, 70, id="envoy_nobatt_metered_3p"),
        pytest.param("envoy_1p_metered", 12, 19, id="envoy_1p_metered"),
        pytest.param("envoy_tot_cons_metered", 5, 8, id="envoy_tot_cons_metered"),
    ],
)


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
async def test_sensor(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy sensor entities."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])

    # number entities states should be created from test data
    assert len(hass.states.async_all()) == entity_count

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    assert len(entity_entries) == enabled_entity_count

    # compare registered entities against snapshot of prior run
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert hass.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_enabled_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy sensor entities."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])

    # number entities states should be created from test data
    assert len(hass.states.async_all()) == enabled_entity_count

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    assert len(entity_entries) == enabled_entity_count

    # compare registered entities against snapshot of prior run
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert hass.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_production_consumption_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    serial_number,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy production entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == enabled_entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.envoy_{serial_number}"

    PRODUCTION_NAMES = (
        "current_power_production",
        "energy_production_today",
        "energy_production_last_seven_days",
        "lifetime_energy_production",
    )
    data = mock_envoy.data.system_production
    PRODUCTION_TARGETS = (
        data.watts_now / 1000.0,
        data.watt_hours_today / 1000.0,
        data.watt_hours_last_7_days / 1000.0,
        data.watt_hours_lifetime / 1000000.0,
    )

    # production sensors is bare minimum and should be defined
    for name, target in zip(PRODUCTION_NAMES, PRODUCTION_TARGETS, strict=False):
        assert target == float(hass.states.get(f"{entity_base}_{name}").state)

    CONSUMPTION_NAMES = (
        "current_power_consumption",
        "energy_consumption_today",
        "energy_consumption_last_seven_days",
        "lifetime_energy_consumption",
    )

    if mock_envoy.data.system_consumption:
        # if consumption is available these should be defined
        data = mock_envoy.data.system_consumption
        CONSUMPTION_TARGETS = (
            data.watts_now / 1000.0,
            data.watt_hours_today / 1000.0,
            data.watt_hours_last_7_days / 1000.0,
            data.watt_hours_lifetime / 1000000.0,
        )
        for name, target in zip(CONSUMPTION_NAMES, CONSUMPTION_TARGETS, strict=False):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

    if not mock_envoy.data.system_consumption:
        # these should not be defined if no consumption is reported
        for name in CONSUMPTION_NAMES:
            assert f"{entity_base}_{name}" not in entity_status

    PRODUCTION_PHASE_NAMES = [
        f"{name}_{phase.lower()}" for phase in PHASENAMES for name in PRODUCTION_NAMES
    ]

    if mock_envoy.data.system_production_phases:
        PRODUCTION_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (
                        phase_data.watts_now / 1000.0,
                        phase_data.watt_hours_today / 1000.0,
                        phase_data.watt_hours_last_7_days / 1000.0,
                        phase_data.watt_hours_lifetime / 1000000.0,
                    )
                    for phase, phase_data in mock_envoy.data.system_production_phases.items()
                ]
            )
        )

        for name, target in zip(
            PRODUCTION_PHASE_NAMES, PRODUCTION_PHASE_TARGET, strict=False
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

    if not mock_envoy.data.system_production_phases:
        # these should not be defined if no phase data is reported
        for name in PRODUCTION_PHASE_NAMES:
            assert f"{entity_base}_{name}" not in entity_status

    CONSUMPTION_PHASE_NAMES = [
        f"{name}_{phase.lower()}" for phase in PHASENAMES for name in CONSUMPTION_NAMES
    ]

    if mock_envoy.data.system_consumption_phases:
        # if envoy reports consumption these should be defined and have data
        CONSUMPTION_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (
                        phase_data.watts_now / 1000.0,
                        phase_data.watt_hours_today / 1000.0,
                        phase_data.watt_hours_last_7_days / 1000.0,
                        phase_data.watt_hours_lifetime / 1000000.0,
                    )
                    for phase, phase_data in mock_envoy.data.system_consumption_phases.items()
                ]
            )
        )

        for name, target in zip(
            CONSUMPTION_PHASE_NAMES, CONSUMPTION_PHASE_TARGET, strict=False
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

    if not mock_envoy.data.system_consumption_phases:
        # if no consumptionphase data test they don't exist
        for name in CONSUMPTION_PHASE_NAMES:
            assert f"{entity_base}_{name}" not in entity_status


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_grid_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    serial_number,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy grid entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == enabled_entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.envoy_{serial_number}"

    CT_CONSUMPTION_NAMES_FLOAT = (
        "lifetime_net_energy_consumption",
        "lifetime_net_energy_production",
        "current_net_power_consumption",
        "frequency_net_consumption_ct",
        "voltage_net_consumption_ct",
        "meter_status_flags_active_net_consumption_ct",
    )
    CT_CONSUMPTION_NAMES_STR = ("metering_status_net_consumption_ct",)

    if mock_envoy.data.ctmeter_consumption and (
        mock_envoy.consumption_meter_type == CtType.NET_CONSUMPTION
    ):
        # if consumption meter data, entities should be created and have values
        data = mock_envoy.data.ctmeter_consumption

        CT_CONSUMPTION_TARGETS_FLOAT = (
            data.energy_delivered / 1000000.0,
            data.energy_received / 1000000.0,
            data.active_power / 1000.0,
            data.frequency,
            data.voltage,
            len(data.status_flags),
        )
        for name, target in zip(
            CT_CONSUMPTION_NAMES_FLOAT, CT_CONSUMPTION_TARGETS_FLOAT, strict=False
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_CONSUMPTION_TARGETS_STR = (data.metering_status,)
        for name, target in zip(
            CT_CONSUMPTION_NAMES_STR, CT_CONSUMPTION_TARGETS_STR, strict=False
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    CT_PRODUCTION_NAMES_FLOAT = ("meter_status_flags_active_production_ct",)
    CT_PRODUCTION_NAMES_STR = ("metering_status_production_ct",)

    if mock_envoy.data.ctmeter_production and (
        mock_envoy.production_meter_type == CtType.PRODUCTION
    ):
        # if production meter data, entities should be created and have values
        data = mock_envoy.data.ctmeter_production

        CT_PRODUCTION_TARGETS_FLOAT = (len(data.status_flags),)
        for name, target in zip(
            CT_PRODUCTION_NAMES_FLOAT, CT_PRODUCTION_TARGETS_FLOAT, strict=False
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_PRODUCTION_TARGETS_STR = (data.metering_status,)
        for name, target in zip(
            CT_PRODUCTION_NAMES_STR, CT_PRODUCTION_TARGETS_STR, strict=False
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    CT_CONSUMPTION_NAMES_FLOAT_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in CT_CONSUMPTION_NAMES_FLOAT
    ]

    CT_CONSUMPTION_NAMES_STR_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in CT_CONSUMPTION_NAMES_STR
    ]

    if mock_envoy.data.ctmeter_consumption_phases and (
        mock_envoy.consumption_meter_type == CtType.NET_CONSUMPTION
    ):
        # if consumption meter phase data, entities should be created and have values
        CT_CONSUMPTION_NAMES_FLOAT_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (
                        phase_data.energy_delivered / 1000000.0,
                        phase_data.energy_received / 1000000.0,
                        phase_data.active_power / 1000.0,
                        phase_data.frequency,
                        phase_data.voltage,
                        len(phase_data.status_flags),
                    )
                    for phase, phase_data in mock_envoy.data.ctmeter_consumption_phases.items()
                ]
            )
        )
        for name, target in zip(
            CT_CONSUMPTION_NAMES_FLOAT_PHASE,
            CT_CONSUMPTION_NAMES_FLOAT_PHASE_TARGET,
            strict=False,
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_CONSUMPTION_NAMES_STR_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (phase_data.metering_status,)
                    for phase, phase_data in mock_envoy.data.ctmeter_consumption_phases.items()
                ]
            )
        )

        for name, target in zip(
            CT_CONSUMPTION_NAMES_STR_PHASE,
            CT_CONSUMPTION_NAMES_STR_PHASE_TARGET,
            strict=False,
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    CT_PRODUCTION_NAMES_FLOAT_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in CT_PRODUCTION_NAMES_FLOAT
    ]

    CT_PRODUCTION_NAMES_STR_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in CT_PRODUCTION_NAMES_STR
    ]

    if mock_envoy.data.ctmeter_production_phases and (
        mock_envoy.production_meter_type == CtType.PRODUCTION
    ):
        # if production meter phase data, entities should be created and have values

        CT_PRODUCTION_NAMES_FLOAT_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (len(phase_data.status_flags),)
                    for phase, phase_data in mock_envoy.data.ctmeter_production_phases.items()
                ]
            )
        )
        for name, target in zip(
            CT_PRODUCTION_NAMES_FLOAT_PHASE,
            CT_PRODUCTION_NAMES_FLOAT_PHASE_TARGET,
            strict=False,
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_PRODUCTION_NAMES_STR_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (phase_data.metering_status,)
                    for phase, phase_data in mock_envoy.data.ctmeter_production_phases.items()
                ]
            )
        )

        for name, target in zip(
            CT_PRODUCTION_NAMES_STR_PHASE,
            CT_PRODUCTION_NAMES_STR_PHASE_TARGET,
            strict=False,
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    if (not mock_envoy.data.ctmeter_consumption) or (
        mock_envoy.consumption_meter_type != CtType.NET_CONSUMPTION
    ):
        # if no ct consumption meter data or not net meter, no entities should be created
        for name in zip(
            CT_CONSUMPTION_NAMES_FLOAT, CT_CONSUMPTION_NAMES_STR, strict=False
        ):
            assert f"{entity_base}_{name}" not in entity_status

    if not mock_envoy.data.ctmeter_production:
        # if no ct production meter data, no entities should be created
        for name in zip(
            CT_PRODUCTION_NAMES_FLOAT, CT_PRODUCTION_NAMES_STR, strict=False
        ):
            assert f"{entity_base}_{name}" not in entity_status

    if (not mock_envoy.data.ctmeter_consumption_phases) or (
        mock_envoy.consumption_meter_type != CtType.NET_CONSUMPTION
    ):
        # if no ct consumption meter phase data or not net meter, no entities should be created
        for name in zip(
            CT_CONSUMPTION_NAMES_FLOAT_PHASE,
            CT_CONSUMPTION_NAMES_STR_PHASE,
            strict=False,
        ):
            assert f"{entity_base}_{name}" not in entity_status

    if not mock_envoy.data.ctmeter_production_phases:
        # if no ct production meter, no entities should be created
        for name in zip(
            CT_PRODUCTION_NAMES_FLOAT_PHASE, CT_PRODUCTION_NAMES_STR_PHASE, strict=False
        ):
            assert f"{entity_base}_{name}" not in entity_status


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_battery_storage_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    serial_number,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy battery storage ct entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == enabled_entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.envoy_{serial_number}"

    CT_STORAGE_NAMES_FLOAT = (
        "lifetime_battery_energy_discharged",
        "lifetime_battery_energy_charged",
        "current_battery_discharge",
        "voltage_storage_ct",
        "meter_status_flags_active_storage_ct",
    )
    CT_STORAGE_NAMES_STR = ("metering_status_storage_ct",)

    if mock_envoy.data.ctmeter_storage:
        # these should be defined and have value from data
        data = mock_envoy.data.ctmeter_storage
        CT_STORAGE_TARGETS_FLOAT = (
            data.energy_delivered / 1000000.0,
            data.energy_received / 1000000.0,
            data.active_power / 1000.0,
            data.voltage,
            len(data.status_flags),
        )
        for name, target in zip(
            CT_STORAGE_NAMES_FLOAT, CT_STORAGE_TARGETS_FLOAT, strict=False
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_STORAGE_TARGETS_STR = (data.metering_status,)
        for name, target in zip(
            CT_STORAGE_NAMES_STR, CT_STORAGE_TARGETS_STR, strict=False
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    CT_STORAGE_NAMES_FLOAT_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in (CT_STORAGE_NAMES_FLOAT)
    ]

    CT_STORAGE_NAMES_STR_PHASE = [
        f"{name}_{phase.lower()}"
        for phase in PHASENAMES
        for name in (CT_STORAGE_NAMES_STR)
    ]

    if mock_envoy.data.ctmeter_storage_phases:
        # if storage meter phase data, entities should be created and have values
        CT_STORAGE_NAMES_FLOAT_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (
                        phase_data.energy_delivered / 1000000.0,
                        phase_data.energy_received / 1000000.0,
                        phase_data.active_power / 1000.0,
                        phase_data.voltage,
                        len(phase_data.status_flags),
                    )
                    for phase, phase_data in mock_envoy.data.ctmeter_storage_phases.items()
                ]
            )
        )
        for name, target in zip(
            CT_STORAGE_NAMES_FLOAT_PHASE,
            CT_STORAGE_NAMES_FLOAT_PHASE_TARGET,
            strict=False,
        ):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

        CT_STORAGE_NAMES_STR_PHASE_TARGET = list(
            itertools.chain(
                *[
                    (phase_data.metering_status,)
                    for phase, phase_data in mock_envoy.data.ctmeter_storage_phases.items()
                ]
            )
        )

        for name, target in zip(
            CT_STORAGE_NAMES_STR_PHASE,
            CT_STORAGE_NAMES_STR_PHASE_TARGET,
            strict=False,
        ):
            assert target == hass.states.get(f"{entity_base}_{name}").state

    if not mock_envoy.data.ctmeter_storage:
        # if no storage ct meter  data these should not be created
        for name in zip(CT_STORAGE_NAMES_FLOAT, CT_STORAGE_NAMES_STR, strict=False):
            assert f"{entity_base}_{name}" not in entity_status

    if not mock_envoy.data.ctmeter_storage_phases:
        # if no storage ct meter phase data these should not be created
        for name in zip(
            CT_STORAGE_NAMES_FLOAT_PHASE, CT_STORAGE_NAMES_STR_PHASE, strict=False
        ):
            assert f"{entity_base}_{name}" not in entity_status


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
async def test_sensor_inverter_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    serial_number,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy inverter entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.inverter"

    for sn, inverter in mock_envoy.data.inverters.items():
        # these should be created and match data
        assert (inverter.last_report_watts) == float(
            hass.states.get(f"{entity_base}_{sn}").state
        )
        # last reported should be disabled
        assert entity_status[f"{entity_base}_{sn}_last_reported"]


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
async def test_sensor_encharge_aggregate_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    serial_number,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy encharge aggregate entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.envoy_{serial_number}"

    ENCHARGE_NAMES = (
        "battery",
        "reserve_battery_level",
        "available_battery_energy",
        "reserve_battery_energy",
        "battery_capacity",
    )

    if mock_envoy.data.encharge_aggregate:
        # these should be defined and have value from data
        data = mock_envoy.data.encharge_aggregate
        ENCHARGE_TARGETS = (
            data.state_of_charge,
            data.reserve_state_of_charge,
            data.available_energy,
            data.backup_reserve,
            data.max_available_capacity,
        )
        for name, target in zip(ENCHARGE_NAMES, ENCHARGE_TARGETS, strict=False):
            assert target == float(hass.states.get(f"{entity_base}_{name}").state)

    if not mock_envoy.data.encharge_aggregate:
        # these should not be created
        for name in ENCHARGE_NAMES:
            assert f"{entity_base}_{name}" not in entity_status


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
async def test_sensor_encharge_enpower_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy enpower entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert entity_registry
    assert len(hass.states.async_all()) == entity_count

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    assert entity_entries

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.enpower_"

    if mock_envoy.data.enpower:
        # these should be defined and have value from data
        sn = mock_envoy.data.enpower.serial_number
        if mock_envoy.data.enpower.temperature_unit == "F":
            assert mock_envoy.data.enpower.temperature == round(
                TemperatureConverter.convert(
                    float(hass.states.get(f"{entity_base}{sn}_temperature").state),
                    hass.config.units.temperature_unit,
                    UnitOfTemperature.FAHRENHEIT,
                )
            )
        else:
            assert mock_envoy.data.enpower.temperature == round(
                TemperatureConverter.convert(
                    float(hass.states.get(f"{entity_base}{sn}_temperature").state),
                    hass.config.units.temperature_unit,
                    UnitOfTemperature.CELSIUS,
                )
            )
        assert dt_util.utc_from_timestamp(
            mock_envoy.data.enpower.last_report_date
        ) == dt_util.parse_datetime(
            hass.states.get(f"{entity_base}{sn}_last_reported").state
        )


@pytest.mark.parametrize(
    ("mock_envoy", "entity_count", "enabled_entity_count"),
    *SENSOR_FIXTURES,
    indirect=["mock_envoy"],
)
async def test_sensor_encharge_power_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_envoy: AsyncMock,
    entity_registry: AsyncMock,
    entity_count: int,
    enabled_entity_count: int,
) -> None:
    """Test enphase_envoy encharge_power entities values and names."""
    await setup_with_selected_platforms(hass, config_entry, [Platform.SENSOR])
    assert len(hass.states.async_all()) == entity_count

    assert entity_registry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    entity_status = {}
    for entity_entry in entity_entries:
        entity_status[entity_entry.entity_id] = entity_entry.disabled_by

    entity_base = f"{Platform.SENSOR}.encharge_"

    ENCHARGE_NAMES = (
        "battery",
        "apparent_power",
        "power",
    )

    if mock_envoy.data.encharge_power:
        # these should be defined and have value from data
        ENCHARGE_TARGETS = [
            (
                sn,
                (
                    encharge_power.soc,
                    encharge_power.apparent_power_mva / 1000.0,
                    encharge_power.real_power_mw / 1000.0,
                ),
            )
            for sn, encharge_power in mock_envoy.data.encharge_power.items()
        ]

        for sn, sn_target in ENCHARGE_TARGETS:
            for name, target in zip(ENCHARGE_NAMES, sn_target, strict=False):
                assert target == float(
                    hass.states.get(f"{entity_base}{sn}_{name}").state
                )

    if mock_envoy.data.encharge_inventory:
        # these should be defined and have value from data
        for sn, encharge_inventory in mock_envoy.data.encharge_inventory.items():
            if encharge_inventory.temperature_unit == "F":
                assert encharge_inventory.temperature == round(
                    TemperatureConverter.convert(
                        float(hass.states.get(f"{entity_base}{sn}_temperature").state),
                        hass.config.units.temperature_unit,
                        UnitOfTemperature.FAHRENHEIT,
                    )
                )
            else:
                assert encharge_inventory.temperature == round(
                    TemperatureConverter.convert(
                        float(hass.states.get(f"{entity_base}{sn}_temperature").state),
                        hass.config.units.temperature_unit,
                        UnitOfTemperature.CELSIUS,
                    )
                )
            assert dt_util.utc_from_timestamp(
                encharge_inventory.last_report_date
            ) == dt_util.parse_datetime(
                hass.states.get(f"{entity_base}{sn}_last_reported").state
            )
