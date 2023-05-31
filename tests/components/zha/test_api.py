"""Test ZHA API."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest
import zigpy.backups
import zigpy.state

from homeassistant.components import zha
from homeassistant.components.zha import api
from homeassistant.components.zha.core.const import RadioType
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from zigpy.application import ControllerApplication


@pytest.fixture(autouse=True)
def required_platform_only():
    """Only set up the required and required base platforms to speed up tests."""
    with patch("homeassistant.components.zha.PLATFORMS", ()):
        yield


async def test_async_get_network_settings_active(
    hass: HomeAssistant, setup_zha
) -> None:
    """Test reading settings with an active ZHA installation."""
    await setup_zha()

    settings = await api.async_get_network_settings(hass)
    assert settings.network_info.channel == 15


async def test_async_get_network_settings_inactive(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test reading settings with an inactive ZHA installation."""
    await setup_zha()

    gateway = api._get_gateway(hass)
    await zha.async_unload_entry(hass, gateway.config_entry)

    backup = zigpy.backups.NetworkBackup()
    backup.network_info.channel = 20
    zigpy_app_controller.backups.backups.append(backup)

    with patch(
        "bellows.zigbee.application.ControllerApplication.__new__",
        return_value=zigpy_app_controller,
    ), patch.object(
        zigpy_app_controller, "_load_db", wraps=zigpy_app_controller._load_db
    ) as mock_load_db, patch.object(
        zigpy_app_controller,
        "start_network",
        wraps=zigpy_app_controller.start_network,
    ) as mock_start_network:
        settings = await api.async_get_network_settings(hass)

    assert len(mock_load_db.mock_calls) == 1
    assert len(mock_start_network.mock_calls) == 0
    assert settings.network_info.channel == 20


async def test_async_get_network_settings_missing(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test reading settings with an inactive ZHA installation, no valid channel."""
    await setup_zha()

    gateway = api._get_gateway(hass)
    await zha.async_unload_entry(hass, gateway.config_entry)

    # Network settings were never loaded for whatever reason
    zigpy_app_controller.state.network_info = zigpy.state.NetworkInfo()
    zigpy_app_controller.state.node_info = zigpy.state.NodeInfo()

    with patch(
        "bellows.zigbee.application.ControllerApplication.__new__",
        return_value=zigpy_app_controller,
    ):
        settings = await api.async_get_network_settings(hass)

    assert settings is None


async def test_async_get_network_settings_failure(hass: HomeAssistant) -> None:
    """Test reading settings with no ZHA config entries and no database."""
    with pytest.raises(ValueError):
        await api.async_get_network_settings(hass)


async def test_async_get_radio_type_active(hass: HomeAssistant, setup_zha) -> None:
    """Test reading the radio type with an active ZHA installation."""
    await setup_zha()

    radio_type = api.async_get_radio_type(hass)
    assert radio_type == RadioType.ezsp


async def test_async_get_radio_path_active(hass: HomeAssistant, setup_zha) -> None:
    """Test reading the radio path with an active ZHA installation."""
    await setup_zha()

    radio_path = api.async_get_radio_path(hass)
    assert radio_path == "/dev/ttyUSB0"


async def test_change_channel(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel."""
    await setup_zha()

    with patch.object(
        zigpy_app_controller, "move_network_to_channel", autospec=True
    ) as mock_move_network_to_channel:
        await api.async_change_channel(hass, 20)

    assert mock_move_network_to_channel.mock_calls == [call(20)]


async def test_change_channel_auto(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel automatically using an energy scan."""
    await setup_zha()

    with patch.object(
        zigpy_app_controller, "move_network_to_channel", autospec=True
    ) as mock_move_network_to_channel, patch.object(
        zigpy_app_controller,
        "energy_scan",
        autospec=True,
        return_value={c: c for c in range(11, 26 + 1)},
    ), patch.object(
        api, "pick_optimal_channel", autospec=True, return_value=25
    ):
        await api.async_change_channel(hass, "auto")

    assert mock_move_network_to_channel.mock_calls == [call(25)]
