"""Statistics helper for sensor."""
from __future__ import annotations

import datetime
import itertools
import logging
from typing import Callable

from homeassistant.components.recorder import history, statistics
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_MONETARY,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL,
    STATE_CLASS_TOTAL_INCREASING,
    STATE_CLASSES,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    DEVICE_CLASS_POWER,
    ENERGY_KILO_WATT_HOUR,
    ENERGY_WATT_HOUR,
    PERCENTAGE,
    POWER_KILO_WATT,
    POWER_WATT,
    PRESSURE_BAR,
    PRESSURE_HPA,
    PRESSURE_INHG,
    PRESSURE_MBAR,
    PRESSURE_PA,
    PRESSURE_PSI,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    TEMP_KELVIN,
    VOLUME_CUBIC_FEET,
    VOLUME_CUBIC_METERS,
)
from homeassistant.core import HomeAssistant, State
import homeassistant.util.dt as dt_util
import homeassistant.util.pressure as pressure_util
import homeassistant.util.temperature as temperature_util
import homeassistant.util.volume as volume_util

from . import ATTR_LAST_RESET, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_OR_UNIT_STATISTICS = {
    STATE_CLASS_TOTAL: {
        DEVICE_CLASS_ENERGY: {"sum"},
        DEVICE_CLASS_GAS: {"sum"},
        DEVICE_CLASS_MONETARY: {"sum"},
    },
    STATE_CLASS_MEASUREMENT: {
        DEVICE_CLASS_BATTERY: {"mean", "min", "max"},
        DEVICE_CLASS_HUMIDITY: {"mean", "min", "max"},
        DEVICE_CLASS_POWER: {"mean", "min", "max"},
        DEVICE_CLASS_PRESSURE: {"mean", "min", "max"},
        DEVICE_CLASS_TEMPERATURE: {"mean", "min", "max"},
        PERCENTAGE: {"mean", "min", "max"},
        # Deprecated, support will be removed in Home Assistant 2021.10
        DEVICE_CLASS_ENERGY: {"sum"},
        DEVICE_CLASS_GAS: {"sum"},
        DEVICE_CLASS_MONETARY: {"sum"},
    },
    STATE_CLASS_TOTAL_INCREASING: {
        DEVICE_CLASS_ENERGY: {"sum"},
        DEVICE_CLASS_GAS: {"sum"},
    },
}

# Normalized units which will be stored in the statistics table
DEVICE_CLASS_UNITS = {
    DEVICE_CLASS_ENERGY: ENERGY_KILO_WATT_HOUR,
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_PRESSURE: PRESSURE_PA,
    DEVICE_CLASS_TEMPERATURE: TEMP_CELSIUS,
    DEVICE_CLASS_GAS: VOLUME_CUBIC_METERS,
}

UNIT_CONVERSIONS: dict[str, dict[str, Callable]] = {
    # Convert energy to kWh
    DEVICE_CLASS_ENERGY: {
        ENERGY_KILO_WATT_HOUR: lambda x: x,
        ENERGY_WATT_HOUR: lambda x: x / 1000,
    },
    # Convert power W
    DEVICE_CLASS_POWER: {
        POWER_WATT: lambda x: x,
        POWER_KILO_WATT: lambda x: x * 1000,
    },
    # Convert pressure to Pa
    # Note: pressure_util.convert is bypassed to avoid redundant error checking
    DEVICE_CLASS_PRESSURE: {
        PRESSURE_BAR: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_BAR],
        PRESSURE_HPA: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_HPA],
        PRESSURE_INHG: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_INHG],
        PRESSURE_MBAR: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_MBAR],
        PRESSURE_PA: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_PA],
        PRESSURE_PSI: lambda x: x / pressure_util.UNIT_CONVERSION[PRESSURE_PSI],
    },
    # Convert temperature to °C
    # Note: temperature_util.convert is bypassed to avoid redundant error checking
    DEVICE_CLASS_TEMPERATURE: {
        TEMP_CELSIUS: lambda x: x,
        TEMP_FAHRENHEIT: temperature_util.fahrenheit_to_celsius,
        TEMP_KELVIN: temperature_util.kelvin_to_celsius,
    },
    # Convert volume to cubic meter
    DEVICE_CLASS_GAS: {
        VOLUME_CUBIC_METERS: lambda x: x,
        VOLUME_CUBIC_FEET: volume_util.cubic_feet_to_cubic_meter,
    },
}

# Keep track of entities for which a warning about unsupported unit has been logged
WARN_UNSUPPORTED_UNIT = set()


def _get_entities(hass: HomeAssistant) -> list[tuple[str, str, str]]:
    """Get (entity_id, state_class, key) of all sensors for which to compile statistics.

    Key is either a device class or a unit and is used to index the
    DEVICE_CLASS_OR_UNIT_STATISTICS map.
    """
    all_sensors = hass.states.all(DOMAIN)
    entity_ids = []

    for state in all_sensors:
        if (state_class := state.attributes.get(ATTR_STATE_CLASS)) not in STATE_CLASSES:
            continue

        if (
            key := state.attributes.get(ATTR_DEVICE_CLASS)
        ) in DEVICE_CLASS_OR_UNIT_STATISTICS[state_class]:
            entity_ids.append((state.entity_id, state_class, key))

        if (
            key := state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        ) in DEVICE_CLASS_OR_UNIT_STATISTICS[state_class]:
            entity_ids.append((state.entity_id, state_class, key))

    return entity_ids


# Faster than try/except
# From https://stackoverflow.com/a/23639915
def _is_number(s: str) -> bool:  # pylint: disable=invalid-name
    """Return True if string is a number."""
    return s.replace(".", "", 1).isdigit()


def _time_weighted_average(
    fstates: list[tuple[float, State]], start: datetime.datetime, end: datetime.datetime
) -> float:
    """Calculate a time weighted average.

    The average is calculated by, weighting the states by duration in seconds between
    state changes.
    Note: there's no interpolation of values between state changes.
    """
    old_fstate: float | None = None
    old_start_time: datetime.datetime | None = None
    accumulated = 0.0

    for fstate, state in fstates:
        # The recorder will give us the last known state, which may be well
        # before the requested start time for the statistics
        start_time = start if state.last_updated < start else state.last_updated
        if old_start_time is None:
            # Adjust start time, if there was no last known state
            start = start_time
        else:
            duration = start_time - old_start_time
            # Accumulate the value, weighted by duration until next state change
            assert old_fstate is not None
            accumulated += old_fstate * duration.total_seconds()

        old_fstate = fstate
        old_start_time = start_time

    if old_fstate is not None:
        # Accumulate the value, weighted by duration until end of the period
        assert old_start_time is not None
        duration = end - old_start_time
        accumulated += old_fstate * duration.total_seconds()

    return accumulated / (end - start).total_seconds()


def _normalize_states(
    entity_history: list[State], key: str, entity_id: str
) -> tuple[str | None, list[tuple[float, State]]]:
    """Normalize units."""
    unit = None

    if key not in UNIT_CONVERSIONS:
        # We're not normalizing this device class, return the state as they are
        fstates = [
            (float(el.state), el) for el in entity_history if _is_number(el.state)
        ]
        if fstates:
            unit = fstates[0][1].attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        return unit, fstates

    fstates = []

    for state in entity_history:
        # Exclude non numerical states from statistics
        if not _is_number(state.state):
            continue

        fstate = float(state.state)
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        # Exclude unsupported units from statistics
        if unit not in UNIT_CONVERSIONS[key]:
            if entity_id not in WARN_UNSUPPORTED_UNIT:
                WARN_UNSUPPORTED_UNIT.add(entity_id)
                _LOGGER.warning("%s has unknown unit %s", entity_id, unit)
            continue

        fstates.append((UNIT_CONVERSIONS[key][unit](fstate), state))

    return DEVICE_CLASS_UNITS[key], fstates


def compile_statistics(
    hass: HomeAssistant, start: datetime.datetime, end: datetime.datetime
) -> dict:
    """Compile statistics for all entities during start-end.

    Note: This will query the database and must not be run in the event loop
    """
    result: dict = {}

    entities = _get_entities(hass)

    # Get history between start and end
    history_list = history.get_significant_states(  # type: ignore
        hass, start - datetime.timedelta.resolution, end, [i[0] for i in entities]
    )

    for entity_id, state_class, key in entities:
        wanted_statistics = DEVICE_CLASS_OR_UNIT_STATISTICS[state_class][key]

        if entity_id not in history_list:
            continue

        entity_history = history_list[entity_id]
        unit, fstates = _normalize_states(entity_history, key, entity_id)

        if not fstates:
            continue

        result[entity_id] = {}

        # Set meta data
        result[entity_id]["meta"] = {
            "unit_of_measurement": unit,
            "has_mean": "mean" in wanted_statistics,
            "has_sum": "sum" in wanted_statistics,
        }

        # Make calculations
        stat: dict = {}
        if "max" in wanted_statistics:
            stat["max"] = max(*itertools.islice(zip(*fstates), 1))
        if "min" in wanted_statistics:
            stat["min"] = min(*itertools.islice(zip(*fstates), 1))

        if "mean" in wanted_statistics:
            stat["mean"] = _time_weighted_average(fstates, start, end)

        if "sum" in wanted_statistics:
            last_reset = old_last_reset = None
            new_state = old_state = None
            _sum = 0
            last_stats = statistics.get_last_statistics(hass, 1, entity_id)
            if entity_id in last_stats:
                # We have compiled history for this sensor before, use that as a starting point
                last_reset = old_last_reset = last_stats[entity_id][0]["last_reset"]
                new_state = old_state = last_stats[entity_id][0]["state"]
                _sum = last_stats[entity_id][0]["sum"]

            for fstate, state in fstates:

                # Deprecated, will be removed in Home Assistant 2021.10
                if (
                    "last_reset" not in state.attributes
                    and state_class == STATE_CLASS_MEASUREMENT
                ):
                    continue

                reset = False
                if (
                    state_class != STATE_CLASS_TOTAL_INCREASING
                    and (last_reset := state.attributes.get("last_reset"))
                    != old_last_reset
                ):
                    reset = True
                elif old_state is None and last_reset is None:
                    reset = True
                elif state_class == STATE_CLASS_TOTAL_INCREASING and (
                    old_state is None or fstate < old_state
                ):
                    reset = True

                if reset:
                    # The sensor has been reset, update the sum
                    if old_state is not None:
                        _sum += new_state - old_state
                    # ..and update the starting point
                    new_state = fstate
                    old_last_reset = last_reset
                    # Force a new cycle for STATE_CLASS_TOTAL_INCREASING to start at 0
                    if state_class == STATE_CLASS_TOTAL_INCREASING and old_state:
                        old_state = 0
                    else:
                        old_state = new_state
                else:
                    new_state = fstate

            # Deprecated, will be removed in Home Assistant 2021.10
            if last_reset is None and state_class == STATE_CLASS_MEASUREMENT:
                # No valid updates
                result.pop(entity_id)
                continue

            if new_state is None or old_state is None:
                # No valid updates
                result.pop(entity_id)
                continue

            # Update the sum with the last state
            _sum += new_state - old_state
            if last_reset is not None:
                stat["last_reset"] = dt_util.parse_datetime(last_reset)
            stat["sum"] = _sum
            stat["state"] = new_state

        result[entity_id]["stat"] = stat

    return result


def list_statistic_ids(hass: HomeAssistant, statistic_type: str | None = None) -> dict:
    """Return statistic_ids and meta data."""
    entities = _get_entities(hass)

    statistic_ids = {}

    for entity_id, state_class, key in entities:
        provided_statistics = DEVICE_CLASS_OR_UNIT_STATISTICS[state_class][key]

        if statistic_type is not None and statistic_type not in provided_statistics:
            continue

        state = hass.states.get(entity_id)
        assert state

        if "sum" in provided_statistics and ATTR_LAST_RESET not in state.attributes:
            continue

        native_unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        if key not in UNIT_CONVERSIONS:
            statistic_ids[entity_id] = native_unit
            continue

        if native_unit not in UNIT_CONVERSIONS[key]:
            continue

        statistics_unit = DEVICE_CLASS_UNITS[key]
        statistic_ids[entity_id] = statistics_unit

    return statistic_ids
