"""Tests for gree component."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.components.climate import DOMAIN
from homeassistant.components.gree.const import (
    COORDINATORS,
    DOMAIN as GREE,
    UPDATE_INTERVAL,
)
from homeassistant.components.gree.coordinator import DeviceDataUpdateCoordinator
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .common import async_setup_gree, build_device_mock

from tests.common import async_fire_time_changed

ENTITY_ID_1 = f"{DOMAIN}.fake_device_1"
ENTITY_ID_2 = f"{DOMAIN}.fake_device_2"


@pytest.fixture
def mock_now():
    """Fixture for dtutil.now."""
    return dt_util.utcnow()


async def test_discovery_after_setup(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, discovery, device, mock_now
) -> None:
    """Test gree devices don't change after multiple discoveries."""
    mock_device_1 = build_device_mock(
        name="fake-device-1", ipAddress="1.1.1.1", mac="aabbcc112233"
    )
    mock_device_2 = build_device_mock(
        name="fake-device-2", ipAddress="2.2.2.2", mac="bbccdd223344"
    )

    discovery.return_value.mock_devices = [mock_device_1, mock_device_2]
    device.side_effect = [mock_device_1, mock_device_2]

    await async_setup_gree(hass)
    await hass.async_block_till_done()

    assert discovery.return_value.scan_count == 1
    assert len(hass.states.async_all(DOMAIN)) == 2

    device_infos = [x.device.device_info for x in hass.data[GREE][COORDINATORS]]
    assert device_infos[0].ip == "1.1.1.1"
    assert device_infos[1].ip == "2.2.2.2"

    # rediscover the same devices with new ip addresses should update
    mock_device_1 = build_device_mock(
        name="fake-device-1", ipAddress="1.1.1.2", mac="aabbcc112233"
    )
    mock_device_2 = build_device_mock(
        name="fake-device-2", ipAddress="2.2.2.1", mac="bbccdd223344"
    )
    discovery.return_value.mock_devices = [mock_device_1, mock_device_2]
    device.side_effect = [mock_device_1, mock_device_2]

    next_update = mock_now + timedelta(minutes=6)
    freezer.move_to(next_update)
    async_fire_time_changed(hass, next_update)
    await hass.async_block_till_done()

    assert discovery.return_value.scan_count == 2
    assert len(hass.states.async_all(DOMAIN)) == 2

    device_infos = [x.device.device_info for x in hass.data[GREE][COORDINATORS]]
    assert device_infos[0].ip == "1.1.1.2"
    assert device_infos[1].ip == "2.2.2.1"


async def test_coordinator_updates(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, discovery, device, mock_now
) -> None:
    """Test gree devices update their state."""
    await async_setup_gree(hass)
    await hass.async_block_till_done()

    assert len(hass.states.async_all(DOMAIN)) == 1

    coordinator = hass.data[GREE][COORDINATORS][0]

    def update_device_state():
        """Update the device state."""
        coordinator.device_state_updated(["test"])

    device().update_state.side_effect = update_device_state

    next_update = mock_now + timedelta(seconds=UPDATE_INTERVAL)
    freezer.move_to(next_update)

    with patch.object(
        DeviceDataUpdateCoordinator, "async_set_updated_data"
    ) as mock_set_updated_data:
        async_fire_time_changed(hass, next_update)
        await hass.async_block_till_done()
        mock_set_updated_data.assert_called_once_with(device().raw_properties)

    assert coordinator.last_update_success is not None
