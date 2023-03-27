"""Test the imap coordinator."""
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from aioimaplib import AUTH, NONAUTH, SELECTED, AioImapException
import pytest

from homeassistant.components.imap import DOMAIN
from homeassistant.components.imap.errors import InvalidAuth, InvalidFolder
from homeassistant.core import Event, HomeAssistant
from homeassistant.util.dt import utcnow

from .const import (
    BAD_SEARCH_RESPONSE,
    TEST_FETCH_RESPONSE_BINARY,
    TEST_FETCH_RESPONSE_HTML,
    TEST_FETCH_RESPONSE_MULTIPART,
    TEST_FETCH_RESPONSE_TEXT_BARE,
    TEST_FETCH_RESPONSE_TEXT_OTHER,
    TEST_FETCH_RESPONSE_TEXT_PLAIN,
    TEST_SEARCH_RESPONSE,
)
from .test_config_flow import MOCK_CONFIG

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.parametrize("imap_search", [TEST_SEARCH_RESPONSE])
@pytest.mark.parametrize(
    "imap_fetch",
    [
        TEST_FETCH_RESPONSE_TEXT_BARE,
        TEST_FETCH_RESPONSE_TEXT_PLAIN,
        TEST_FETCH_RESPONSE_TEXT_OTHER,
        TEST_FETCH_RESPONSE_HTML,
        TEST_FETCH_RESPONSE_MULTIPART,
        TEST_FETCH_RESPONSE_BINARY,
    ],
    ids=["bare", "plain", "other", "html", "multipart", "binary"],
)
@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}, set()], ids=["push", "poll"])
async def test_receiving_message_successfully(
    hass: HomeAssistant, mock_imap_protocol: MagicMock
) -> None:
    """Test receiving a message successfully."""
    event_called = MagicMock()

    async def _async_event_listener(event: Event) -> None:
        """Listen to events."""
        event_called(event)

    handler = hass.bus.async_listen("imap_content", _async_event_listener)

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # Make sure we have had one update (when polling)
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    state = hass.states.get("sensor.imap_email_email_com")
    # we should have received one message
    assert state is not None
    assert state.state == "1"

    # cleanup event listener
    handler()

    # we should have received one event
    event_called.assert_called_once()


@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}, set()], ids=["push", "poll"])
@pytest.mark.parametrize(
    ("imap_login_state", "success"), [(AUTH, True), (NONAUTH, False)]
)
async def test_initial_authentication_error(
    hass: HomeAssistant, mock_imap_protocol: MagicMock, success: bool
) -> None:
    """Test authentication error."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id) == success
    await hass.async_block_till_done()


@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}, set()], ids=["push", "poll"])
@pytest.mark.parametrize(
    ("imap_select_state", "success"), [(AUTH, False), (SELECTED, True)]
)
async def test_initial_invalid_folder_error(
    hass: HomeAssistant, mock_imap_protocol: MagicMock, success: bool
) -> None:
    """Test receiving a message successfully."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id) == success
    await hass.async_block_till_done()


@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}, set()], ids=["push", "poll"])
@pytest.mark.parametrize("imap_search", [BAD_SEARCH_RESPONSE])
@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (InvalidAuth, "Username or password incorrect, starting reauthentication"),
        (InvalidFolder, "Selected mailbox folder is invalid"),
    ],
)
async def test_late_authentication_or_invalid_folder_error(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    mock_imap_protocol: MagicMock,
    imap_capabilities: set[str],
    exception: InvalidAuth | InvalidFolder,
    error_message: str,
) -> None:
    """Test authentication error after search was failed."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)

    if imap_capabilities == set():
        # Avoid first refresh when polling to avoid a failing entry setup
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh"
        ):
            assert await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()
    else:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    # Make sure we have had at least one update (when polling)
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=60))
    await hass.async_block_till_done()
    with patch(
        "homeassistant.components.imap.coordinator.connect_to_server",
        side_effect=exception,
    ):
        # Make sure we have had at least one update (when polling)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=60))
        await hass.async_block_till_done()
        assert error_message in caplog.text


@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}, set()], ids=["push", "poll"])
@pytest.mark.parametrize(
    "imap_close",
    [
        AsyncMock(side_effect=AioImapException("Something went wrong")),
        AsyncMock(side_effect=asyncio.TimeoutError),
    ],
    ids=["AioImapException", "TimeoutError"],
)
async def test_handle_cleanup_exception(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, mock_imap_protocol: MagicMock
) -> None:
    """Test receiving a message successfully."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # Make sure we have had one update (when polling)
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    assert await config_entry.async_unload(hass)
    await hass.async_block_till_done()
    assert "Error while cleaning up imap connection" in caplog.text


@pytest.mark.parametrize("imap_capabilities", [{"IDLE"}], ids=["push"])
@pytest.mark.parametrize(
    "imap_wait_server_push",
    [
        AsyncMock(side_effect=AioImapException("Something went wrong")),
        AsyncMock(side_effect=asyncio.TimeoutError),
    ],
    ids=["AioImapException", "TimeoutError"],
)
async def test_last_connection_with_imap_push(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, mock_imap_protocol: MagicMock
) -> None:
    """Test receiving a message successfully."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert "Lost imap.server.com (will attempt to reconnect after 10 s)" in caplog.text
