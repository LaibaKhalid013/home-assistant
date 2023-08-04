"""Test stt."""
from __future__ import annotations

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from wyoming.wake import Detection

from homeassistant.components import wake_word
from homeassistant.core import HomeAssistant

from . import MockAsyncTcpClient


async def test_support(hass: HomeAssistant, init_wyoming_wake_word) -> None:
    """Test supported properties."""
    state = hass.states.get("wake_word.test_wake_word")
    assert state is not None

    entity = wake_word.async_get_wake_word_detection_entity(
        hass, "wake_word.test_wake_word"
    )
    assert entity is not None

    assert entity.supported_wake_words == [
        wake_word.WakeWord(ww_id="Test Model", name="Test Model")
    ]


async def test_streaming_audio(
    hass: HomeAssistant, init_wyoming_wake_word, snapshot: SnapshotAssertion
) -> None:
    """Test streaming audio."""
    entity = wake_word.async_get_wake_word_detection_entity(
        hass, "wake_word.test_wake_word"
    )
    assert entity is not None

    async def audio_stream():
        yield "chunk1", 1000
        yield "chunk2", 2000

    with patch(
        "homeassistant.components.wyoming.wake_word.AsyncTcpClient",
        MockAsyncTcpClient([Detection(name="Test Model", timestamp=1000).event()]),
    ):
        result = await entity.async_process_audio_stream(audio_stream())

    assert result is not None
    assert result == snapshot


async def test_streaming_audio_connection_lost(
    hass: HomeAssistant, init_wyoming_wake_word
) -> None:
    """Test streaming audio and losing connection."""
    entity = wake_word.async_get_wake_word_detection_entity(
        hass, "wake_word.test_wake_word"
    )
    assert entity is not None

    async def audio_stream():
        yield "chunk1", 1000

    with patch(
        "homeassistant.components.wyoming.wake_word.AsyncTcpClient",
        MockAsyncTcpClient([None]),
    ):
        result = await entity.async_process_audio_stream(audio_stream())

    assert result is None


async def test_streaming_audio_oserror(
    hass: HomeAssistant, init_wyoming_wake_word
) -> None:
    """Test streaming audio and error raising."""
    entity = wake_word.async_get_wake_word_detection_entity(
        hass, "wake_word.test_wake_word"
    )
    assert entity is not None

    async def audio_stream():
        yield "chunk1", 1000

    mock_client = MockAsyncTcpClient(
        [Detection(name="Test Model", timestamp=1000).event()]
    )

    with patch(
        "homeassistant.components.wyoming.wake_word.AsyncTcpClient",
        mock_client,
    ), patch.object(mock_client, "read_event", side_effect=OSError("Boom!")):
        result = await entity.async_process_audio_stream(audio_stream())

    assert result is None
