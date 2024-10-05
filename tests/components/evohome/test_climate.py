"""The tests for climate entities of evohome.

All evohome systems have controllers and at least one zone.
"""

from __future__ import annotations

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy import SnapshotAssertion

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .conftest import get_zone_entity, setup_evohome
from .const import TEST_INSTALLS


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zon_set_hvac_mode(
    hass: HomeAssistant,
    config: dict[str, str],
    install: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate methods of a evohome-compatible zone."""

    results = []

    async for _ in setup_evohome(hass, config, install=install):
        zone = get_zone_entity(hass)

        assert zone.hvac_modes == [HVACMode.OFF, HVACMode.HEAT]

        # set_hvac_mode(HVACMode.HEAT): FollowSchedule
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_hvac_mode(HVACMode.HEAT)

            assert mock_fcn.await_count == 1
            assert install != "default" or mock_fcn.await_args.args == (
                {
                    "setpointMode": "FollowSchedule",
                },
            )
            assert mock_fcn.await_args.kwargs == {}

        # set_hvac_mode(HVACMode.OFF): PermanentOverride, minHeatSetpoint
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_hvac_mode(HVACMode.OFF)

            assert mock_fcn.await_count == 1
            assert install != "default" or mock_fcn.await_args.args == (
                {
                    "setpointMode": "PermanentOverride",
                    "HeatSetpointValue": 5.0,  # varies by install
                },
            )
            assert mock_fcn.await_args.kwargs == {}

            results.append(mock_fcn.await_args.args)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zon_set_preset_mode(
    hass: HomeAssistant,
    config: dict[str, str],
    install: str,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate methods of a evohome-compatible zone."""

    freezer.move_to("2024-07-10T12:00:00Z")
    results = []

    async for _ in setup_evohome(hass, config, install=install):
        zone = get_zone_entity(hass)

        assert zone.preset_modes == ["none", "temporary", "permanent"]

        # set_preset_mode(none): FollowSchedule
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_preset_mode("none")

            assert mock_fcn.await_count == 1
            assert mock_fcn.await_args.args == (
                {
                    "setpointMode": "FollowSchedule",
                },
            )
            assert mock_fcn.await_args.kwargs == {}

        # set_preset_mode(permanent): PermanentOverride
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_preset_mode("permanent")

            assert mock_fcn.await_count == 1
            assert install != "default" or mock_fcn.await_args.args == (
                {
                    "setpointMode": "PermanentOverride",
                    "HeatSetpointValue": 17.0,  # varies by install
                },
            )
            assert mock_fcn.await_args.kwargs == {}

            results.append(mock_fcn.await_args.args)

        # set_preset_mode(permanent): TemporaryOverride
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_preset_mode("temporary")

            assert mock_fcn.await_count == 1
            assert install != "default" or mock_fcn.await_args.args == (
                {
                    "setpointMode": "TemporaryOverride",
                    "HeatSetpointValue": 17.0,  # varies by install
                    "timeUntil": "2024-07-10T21:10:00Z",  # varies by install
                },
            )
            assert mock_fcn.await_args.kwargs == {}

            results.append(mock_fcn.await_args.args)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zon_set_temperature(
    hass: HomeAssistant,
    config: dict[str, str],
    install: str,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test climate methods of a evohome-compatible zone."""

    freezer.move_to("2024-07-10T12:00:00Z")
    results = []

    async for _ in setup_evohome(hass, config, install=install):
        zone = get_zone_entity(hass)

        # set_temperature(temp): TemporaryOverride, advanced
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_temperature(temperature=19.1)

            assert mock_fcn.await_count == 1
            assert install != "default" or mock_fcn.await_args.args == (
                {
                    "setpointMode": "TemporaryOverride",
                    "HeatSetpointValue": 19.1,
                    "timeUntil": "2024-07-10T21:10:00Z",  # varies by install
                },
            )
            assert mock_fcn.await_args.kwargs == {}

            results.append(mock_fcn.await_args.args)

        # set_temperature(temp, until): TemporaryOverride, until
        with patch("evohomeasync2.zone.Zone._set_mode") as mock_fcn:
            await zone.async_set_temperature(
                temperature=19.2,
                until=dt_util.parse_datetime("2024-07-10T13:30:00Z"),
            )

            assert mock_fcn.await_count == 1
            assert mock_fcn.await_args.args == (
                {
                    "setpointMode": "TemporaryOverride",
                    "HeatSetpointValue": 19.2,
                    "timeUntil": "2024-07-10T13:30:00Z",
                },
            )
            assert mock_fcn.await_args.kwargs == {}

    assert results == snapshot
