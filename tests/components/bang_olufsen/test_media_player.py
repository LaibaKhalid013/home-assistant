"""Test the Bang & Olufsen media_player entity."""

from unittest.mock import patch

import pytest

from homeassistant.components.bang_olufsen.const import (
    BANG_OLUFSEN_STATES,
    DOMAIN,
    WebsocketNotification,
)
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_ALBUM_ARTIST,
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CHANNEL,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_EXTRA,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_TRACK,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.setup import async_setup_component

from .const import (
    TEST_AUDIO_SOURCES,
    TEST_DEEZER_FLOW,
    TEST_DEEZER_INVALID_FLOW,
    TEST_DEEZER_PLAYLIST,
    TEST_DEEZER_TRACK,
    TEST_FALLBACK_SOURCES,
    TEST_MEDIA_PLAYER_ENTITY_ID,
    TEST_OVERLAY_INVALID_OFFSET_VOLUME_TTS,
    TEST_OVERLAY_OFFSET_VOLUME_TTS,
    # TEST_PLAYBACK_ERROR,
    TEST_PLAYBACK_METADATA,
    TEST_PLAYBACK_PROGRESS,
    TEST_PLAYBACK_STATE_PAUSED,
    TEST_PLAYBACK_STATE_PLAYING,
    TEST_PLAYBACK_STATE_TURN_OFF,
    TEST_RADIO_STATION,
    TEST_SEEK_POSITION_HOME_ASSISTANT_FORMAT,
    TEST_SERIAL_NUMBER,
    TEST_SOURCE_CHANGE,
    TEST_SOURCE_CHANGE_DEEZER,
    TEST_SOURCE_CHANGE_URI_STREAMER,
    TEST_SOURCES,
    TEST_VIDEO_SOURCES,
    TEST_VOLUME,
    TEST_VOLUME_HOME_ASSISTANT_FORMAT,
    TEST_VOLUME_MUTED,
    TEST_VOLUME_MUTED_HOME_ASSISTANT_FORMAT,
)

from tests.common import MockConfigEntry


async def test_initialization(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_mozart_client
) -> None:
    """Test the integration is initialized properly in _initialize, async_added_to_hass and __init__."""

    # Setup entity
    with patch(
        "homeassistant.components.bang_olufsen.media_player._LOGGER.debug"
    ) as mock_logger:
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Ensure that the logger has been called with the debug message
    mock_logger.assert_called_once_with(
        "Connected to: %s %s running SW %s", "Beosound Balance", "11111111", "1.0.0"
    )

    # Check state (The initial state in this test does not contain all that much.
    # States are tested using simulated WebSocket events.)
    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.attributes[ATTR_INPUT_SOURCE_LIST] == TEST_SOURCES
    assert states.attributes[ATTR_MEDIA_POSITION_UPDATED_AT]

    # Check API calls
    mock_mozart_client.get_softwareupdate_status.assert_called_once()
    mock_mozart_client.get_product_state.assert_called_once()
    mock_mozart_client.get_available_sources.assert_called_once()
    mock_mozart_client.get_remote_menu.assert_called_once()


async def test_async_update_sources_audio_only(
    hass: HomeAssistant, mock_config_entry, mock_mozart_client
) -> None:
    """Test sources are correctly handled in _async_update_sources."""
    mock_mozart_client.get_remote_menu.return_value = {}

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.attributes[ATTR_INPUT_SOURCE_LIST] == TEST_AUDIO_SOURCES


async def test_async_update_sources_outdated_api(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test fallback sources are correctly handled in _async_update_sources."""
    mock_mozart_client.get_available_sources.side_effect = ValueError()

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert (
        states.attributes[ATTR_INPUT_SOURCE_LIST]
        == TEST_FALLBACK_SOURCES + TEST_VIDEO_SOURCES
    )


async def test_async_update_playback_metadata(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test _async_update_playback_metadata."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_MEDIA_DURATION not in states.attributes
    assert ATTR_MEDIA_TITLE not in states.attributes
    assert ATTR_MEDIA_ALBUM_NAME not in states.attributes
    assert ATTR_MEDIA_ALBUM_ARTIST not in states.attributes
    assert ATTR_MEDIA_TRACK not in states.attributes
    assert ATTR_MEDIA_CHANNEL not in states.attributes

    # Send the WebSocket event dispatch
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_METADATA}",
        TEST_PLAYBACK_METADATA,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert (
        states.attributes[ATTR_MEDIA_DURATION]
        == TEST_PLAYBACK_METADATA.total_duration_seconds
    )
    assert states.attributes[ATTR_MEDIA_TITLE] == TEST_PLAYBACK_METADATA.title
    assert states.attributes[ATTR_MEDIA_ALBUM_NAME] == TEST_PLAYBACK_METADATA.album_name
    assert (
        states.attributes[ATTR_MEDIA_ALBUM_ARTIST] == TEST_PLAYBACK_METADATA.artist_name
    )
    assert states.attributes[ATTR_MEDIA_TRACK] == TEST_PLAYBACK_METADATA.track
    assert states.attributes[ATTR_MEDIA_CHANNEL] == TEST_PLAYBACK_METADATA.organization


# async def test_async_update_playback_error(
#     hass: HomeAssistant, mock_mozart_client, mock_config_entry
# ) -> None:
#     """Test _async_update_playback_error."""

#     mock_config_entry.add_to_hass(hass)
#     await hass.config_entries.async_setup(mock_config_entry.entry_id)

#     with pytest.raises(HomeAssistantError) as exc_info:
#         async_dispatcher_send(
#             hass,
#             f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_ERROR}",
#             TEST_PLAYBACK_ERROR,
#         )

#     assert exc_info.errisinstance(HomeAssistantError)


async def test_async_update_playback_progress(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test _async_update_playback_progress."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_MEDIA_POSITION not in states.attributes
    old_updated_at = states.attributes[ATTR_MEDIA_POSITION_UPDATED_AT]
    assert old_updated_at

    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_PROGRESS}",
        TEST_PLAYBACK_PROGRESS,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.attributes[ATTR_MEDIA_POSITION] == TEST_PLAYBACK_PROGRESS.progress
    new_updated_at = states.attributes[ATTR_MEDIA_POSITION_UPDATED_AT]
    assert new_updated_at
    assert old_updated_at != new_updated_at


async def test_async_update_playback_state(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test _async_update_playback_state."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == MediaPlayerState.PLAYING

    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_STATE}",
        TEST_PLAYBACK_STATE_PAUSED,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == TEST_PLAYBACK_STATE_PAUSED.value


async def test_async_update_source_change(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test _async_update_source_change."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_INPUT_SOURCE not in states.attributes

    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.SOURCE_CHANGE}",
        TEST_SOURCE_CHANGE,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.attributes[ATTR_INPUT_SOURCE] == TEST_SOURCE_CHANGE.name


async def test_async_update_source_change_uri_streamer(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test _async_update_source_change switching to uri_streamer."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_INPUT_SOURCE not in states.attributes
    assert states.attributes[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC

    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.SOURCE_CHANGE}",
        TEST_SOURCE_CHANGE_URI_STREAMER,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.attributes[ATTR_INPUT_SOURCE] == TEST_SOURCE_CHANGE_URI_STREAMER.name
    assert states.attributes[ATTR_MEDIA_CONTENT_TYPE] == MediaType.URL


async def test_async_turn_off(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_turn_off."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "turn_off",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_STATE}",
        TEST_PLAYBACK_STATE_TURN_OFF,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == BANG_OLUFSEN_STATES[TEST_PLAYBACK_STATE_TURN_OFF.value]

    # Check API call
    mock_mozart_client.post_standby.assert_called_once()


async def test_async_set_volume_level(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_set_volume_level and _async_update_volume by proxy."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_MEDIA_VOLUME_LEVEL not in states.attributes

    await hass.services.async_call(
        "media_player",
        "volume_set",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_VOLUME_LEVEL: TEST_VOLUME_HOME_ASSISTANT_FORMAT,
        },
    )

    # The service call will trigger a WebSocket notification
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.VOLUME}",
        TEST_VOLUME,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert (
        states.attributes[ATTR_MEDIA_VOLUME_LEVEL] == TEST_VOLUME_HOME_ASSISTANT_FORMAT
    )

    mock_mozart_client.set_current_volume_level.assert_called_once_with(
        volume_level=TEST_VOLUME.level
    )


async def test_async_mute_volume(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_mute_volume."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert ATTR_MEDIA_VOLUME_MUTED not in states.attributes

    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_VOLUME_MUTED: TEST_VOLUME_HOME_ASSISTANT_FORMAT,
        },
    )

    # The service call will trigger a WebSocket notification
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.VOLUME}",
        TEST_VOLUME_MUTED,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert (
        states.attributes[ATTR_MEDIA_VOLUME_MUTED]
        == TEST_VOLUME_MUTED_HOME_ASSISTANT_FORMAT
    )

    mock_mozart_client.set_volume_mute.assert_called_once_with(
        volume_mute=TEST_VOLUME_MUTED.muted
    )


async def test_async_media_play_pause_pause(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_play_pause pausing."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the state to playing
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_STATE}",
        TEST_PLAYBACK_STATE_PLAYING,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == BANG_OLUFSEN_STATES[TEST_PLAYBACK_STATE_PLAYING.value]

    await hass.services.async_call(
        "media_player",
        "media_play_pause",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    mock_mozart_client.post_playback_command.assert_called_once_with(command="pause")


async def test_async_media_play_pause_play(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_play_pause playing."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the state to paused
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_STATE}",
        TEST_PLAYBACK_STATE_PAUSED,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == BANG_OLUFSEN_STATES[TEST_PLAYBACK_STATE_PAUSED.value]

    await hass.services.async_call(
        "media_player",
        "media_play_pause",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    mock_mozart_client.post_playback_command.assert_called_once_with(command="play")


async def test_async_media_stop(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_stop."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the state to playing
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.PLAYBACK_STATE}",
        TEST_PLAYBACK_STATE_PLAYING,
    )

    states = hass.states.get(TEST_MEDIA_PLAYER_ENTITY_ID)
    assert states.state == BANG_OLUFSEN_STATES[TEST_PLAYBACK_STATE_PLAYING.value]

    await hass.services.async_call(
        "media_player",
        "media_stop",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    # Check API call
    mock_mozart_client.post_playback_command.assert_called_once_with(command="stop")


async def test_async_media_next_track(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_next_track."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "media_next_track",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    mock_mozart_client.post_playback_command.assert_called_once_with(command="skip")


async def test_async_media_seek_not_deezer(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_seek for a source other than Deezer."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the source to Tidal Connect
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.SOURCE_CHANGE}",
        TEST_SOURCE_CHANGE,
    )

    # Ensure that the HomeAssistantError is raised
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            "media_player",
            "media_seek",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_MEDIA_SEEK_POSITION: TEST_SEEK_POSITION_HOME_ASSISTANT_FORMAT,
            },
            blocking=True,
        )

    # Check exception details
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "non_deezer_seeking"
    assert exc_info.errisinstance(HomeAssistantError)

    mock_mozart_client.seek_to_position.assert_not_called()


async def test_async_media_seek_deezer(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_seek for Deezer as source."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the source to Deezer
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.SOURCE_CHANGE}",
        TEST_SOURCE_CHANGE_DEEZER,
    )

    await hass.services.async_call(
        "media_player",
        "media_seek",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_SEEK_POSITION: TEST_SEEK_POSITION_HOME_ASSISTANT_FORMAT,
        },
    )

    mock_mozart_client.seek_to_position.assert_called_once_with(position_ms=10000)


async def test_async_media_previous_track(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_media_previous_track."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "media_previous_track",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    mock_mozart_client.post_playback_command.assert_called_once_with(command="prev")


async def test_async_clear_playlist(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_clear_playlist."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "clear_playlist",
        {ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID},
    )

    mock_mozart_client.post_clear_queue.assert_called_once()


async def test_async_select_source_invalid(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_select_source with an invalid source."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            "media_player",
            "select_source",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_INPUT_SOURCE: "Test source",
            },
            blocking=True,
        )

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "invalid_source"
    assert exc_info.errisinstance(HomeAssistantError)

    mock_mozart_client.set_active_source.assert_not_called()
    mock_mozart_client.post_remote_trigger.assert_not_called()


async def test_async_select_source_audio(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_select_source with a valid audio source."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_INPUT_SOURCE: TEST_SOURCE_CHANGE.name,
        },
    )

    mock_mozart_client.set_active_source.assert_called_once_with(
        source_id=TEST_SOURCE_CHANGE.id
    )
    mock_mozart_client.post_remote_trigger.assert_not_called()


async def test_async_select_source_video(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_select_source with a valid video source."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_INPUT_SOURCE: TEST_VIDEO_SOURCES[0],
        },
    )

    mock_mozart_client.set_active_source.assert_not_called()
    mock_mozart_client.post_remote_trigger.assert_called_once()


async def test_async_play_media_invalid_type(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media only accepts valid media types."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_MEDIA_CONTENT_ID: "test",
                ATTR_MEDIA_CONTENT_TYPE: "invalid type",
            },
            blocking=True,
        )

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "invalid_media_type"
    assert exc_info.errisinstance(HomeAssistantError)


async def test_async_play_media_url(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media URL."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Setup media source
    await async_setup_component(hass, "media_source", {"media_source": {}})

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "media-source://media_source/local/doorbell.mp3",
            ATTR_MEDIA_CONTENT_TYPE: "audio/mpeg",
        },
    )

    mock_mozart_client.post_uri_source.assert_called_once()


async def test_async_play_media_overlay_absolute_volume_uri(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media overlay with Home Assistant local URI and absolute volume."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await async_setup_component(hass, "media_source", {"media_source": {}})

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "media-source://media_source/local/doorbell.mp3",
            ATTR_MEDIA_CONTENT_TYPE: "music",
            ATTR_MEDIA_ANNOUNCE: True,
            ATTR_MEDIA_EXTRA: {"overlay_absolute_volume": 60},
        },
    )

    mock_mozart_client.post_overlay_play.assert_called_once()

    # Check that the API call was as expected
    args, _ = mock_mozart_client.post_overlay_play.call_args
    assert args[0].volume_absolute == 60
    assert "/local/doorbell.mp3" in args[0].uri.location


async def test_async_play_media_overlay_invalid_offset_volume_tts(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Home Assistant invalid offset volume and B&O tts."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    with patch(
        "homeassistant.components.bang_olufsen.media_player._LOGGER.warning"
    ) as mock_logger:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_MEDIA_CONTENT_ID: "Dette er en test",
                ATTR_MEDIA_CONTENT_TYPE: "overlay_tts",
                ATTR_MEDIA_ANNOUNCE: True,
                ATTR_MEDIA_EXTRA: {
                    "overlay_offset_volume": 20,
                    "overlay_tts_language": "da-dk",
                },
            },
        )
        mock_logger.assert_called_once_with("Error setting volume")

    mock_mozart_client.post_overlay_play.assert_called_once_with(
        TEST_OVERLAY_INVALID_OFFSET_VOLUME_TTS
    )


async def test_async_play_media_overlay_offset_volume_tts(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Home Assistant invalid offset volume and B&O tts."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Set the volume to enable offset
    async_dispatcher_send(
        hass,
        f"{TEST_SERIAL_NUMBER}_{WebsocketNotification.VOLUME}",
        TEST_VOLUME,
    )

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "This is a test",
            ATTR_MEDIA_CONTENT_TYPE: "overlay_tts",
            ATTR_MEDIA_ANNOUNCE: True,
            ATTR_MEDIA_EXTRA: {"overlay_offset_volume": 20},
        },
    )

    mock_mozart_client.post_overlay_play.assert_called_once_with(
        TEST_OVERLAY_OFFSET_VOLUME_TTS
    )


async def test_async_play_media_tts(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Home Assistant tts."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await async_setup_component(hass, "media_source", {"media_source": {}})

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "media-source://media_source/local/doorbell.mp3",
            ATTR_MEDIA_CONTENT_TYPE: "provider",
        },
    )

    mock_mozart_client.post_overlay_play.assert_called_once()


async def test_async_play_media_radio(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with B&O radio."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "1234567890123456",
            ATTR_MEDIA_CONTENT_TYPE: "radio",
        },
    )

    mock_mozart_client.run_provided_scene.assert_called_once_with(
        scene_properties=TEST_RADIO_STATION
    )


async def test_async_play_media_favourite(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with B&O favourite."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "1",
            ATTR_MEDIA_CONTENT_TYPE: "favourite",
        },
    )

    mock_mozart_client.activate_preset.assert_called_once_with(id=int("1"))


async def test_async_play_media_deezer_flow(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Deezer flow."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    # Send a service call
    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "flow",
            ATTR_MEDIA_CONTENT_TYPE: "deezer",
            ATTR_MEDIA_EXTRA: {"id": "123"},
        },
    )

    mock_mozart_client.start_deezer_flow.assert_called_once_with(
        user_flow=TEST_DEEZER_FLOW
    )


async def test_async_play_media_deezer_playlist(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Deezer playlist."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "playlist:1234567890",
            ATTR_MEDIA_CONTENT_TYPE: "deezer",
            ATTR_MEDIA_EXTRA: {"start_from": 123},
        },
    )

    mock_mozart_client.add_to_queue.assert_called_once_with(
        play_queue_item=TEST_DEEZER_PLAYLIST
    )


async def test_async_play_media_deezer_track(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with Deezer track."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: "1234567890",
            ATTR_MEDIA_CONTENT_TYPE: "deezer",
        },
    )

    mock_mozart_client.add_to_queue.assert_called_once_with(
        play_queue_item=TEST_DEEZER_TRACK
    )


async def test_async_play_media_invalid_deezer(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media with an invalid/no Deezer login."""

    mock_mozart_client.start_deezer_flow.side_effect = TEST_DEEZER_INVALID_FLOW

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_MEDIA_CONTENT_ID: "flow",
                ATTR_MEDIA_CONTENT_TYPE: "deezer",
            },
            blocking=True,
        )

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "play_media_error"
    assert exc_info.errisinstance(HomeAssistantError)

    mock_mozart_client.start_deezer_flow.assert_called_once()


async def test_async_play_media_url_m3u(
    hass: HomeAssistant, mock_mozart_client, mock_config_entry
) -> None:
    """Test async_play_media URL with the m3u extension."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    await async_setup_component(hass, "media_source", {"media_source": {}})

    with (
        pytest.raises(HomeAssistantError) as exc_info,
        patch(
            "homeassistant.components.bang_olufsen.media_player.async_process_play_media_url",
            return_value="https://test.com/test.m3u",
        ),
    ):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                ATTR_ENTITY_ID: TEST_MEDIA_PLAYER_ENTITY_ID,
                ATTR_MEDIA_CONTENT_ID: "media-source://media_source/local/doorbell.mp3",
                ATTR_MEDIA_CONTENT_TYPE: "audio/mpeg",
            },
            blocking=True,
        )

    # Check exception
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "m3u_invalid_format"
    assert exc_info.errisinstance(HomeAssistantError)

    mock_mozart_client.post_uri_source.assert_not_called()
