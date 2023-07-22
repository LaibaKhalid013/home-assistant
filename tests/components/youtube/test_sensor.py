"""Sensor tests for the YouTube integration."""
from datetime import timedelta
from unittest.mock import patch

from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import MockYouTube
from .conftest import ComponentSetup

from tests.common import async_fire_time_changed


async def test_sensor(
    hass: HomeAssistant, snapshot: SnapshotAssertion, setup_integration: ComponentSetup
) -> None:
    """Test sensor."""
    await setup_integration()

    state = hass.states.get("sensor.google_for_developers_latest_upload")
    assert state == snapshot

    state = hass.states.get("sensor.google_for_developers_subscribers")
    assert state == snapshot


async def test_sensor_updating(
    hass: HomeAssistant, setup_integration: ComponentSetup
) -> None:
    """Test updating sensor."""
    await setup_integration()

    state = hass.states.get("sensor.google_for_developers_latest_upload")
    assert state
    assert state.attributes["video_id"] == "wysukDrMdqU"

    with patch(
        "homeassistant.components.youtube.api.YouTube",
        return_value=MockYouTube(
            playlist_items_fixture="youtube/get_playlist_items_2.json"
        ),
    ):
        future = dt_util.utcnow() + timedelta(minutes=15)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()
    state = hass.states.get("sensor.google_for_developers_latest_upload")
    assert state
    assert state.name == "Google for Developers Latest upload"
    assert state.state == "Google I/O 2023 Developer Keynote in 5 minutes"
    assert (
        state.attributes["entity_picture"]
        == "https://i.ytimg.com/vi/hleLlcHwQLM/maxresdefault.jpg"
    )
    assert state.attributes["video_id"] == "hleLlcHwQLM"
