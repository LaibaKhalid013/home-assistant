"""Tests for the Sonos Media Browser."""

from functools import partial

from pytest_unordered import unordered

from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.components.media_player.const import MediaClass, MediaType
from homeassistant.components.sonos.media_browser import (
    build_item_response,
    get_thumbnail_url_full,
)
from homeassistant.core import HomeAssistant

from .conftest import SoCoMockFactory

from tests.typing import WebSocketGenerator


class MockMusicServiceItem:
    """Mocks a Soco MusicServiceItem."""

    def __init__(
        self,
        title: str,
        item_id: str,
        parent_id: str,
        item_class: str,
    ) -> None:
        """Initialize the mock item."""
        self.title = title
        self.item_id = item_id
        self.item_class = item_class
        self.parent_id = parent_id

    def get_uri(self) -> str:
        """Return URI."""
        return self.item_id.replace("S://", "x-file-cifs://")


def mock_browse_by_idstring(
    search_type: str, idstring: str, start=0, max_items=100, full_album_art_uri=False
) -> list[MockMusicServiceItem]:
    """Mock the call to browse_by_id_string."""
    if search_type == "albums" and idstring in (
        "A:ALBUM/Abbey%20Road",
        "A:ALBUM/Abbey Road",
    ):
        return [
            MockMusicServiceItem(
                "Come Together",
                "S://192.168.42.10/music/The%20Beatles/Abbey%20Road/01%20Come%20Together.mp3",
                "A:ALBUM/Abbey%20Road",
                "object.item.audioItem.musicTrack",
            ),
            MockMusicServiceItem(
                "Something",
                "S://192.168.42.10/music/The%20Beatles/Abbey%20Road/03%20Something.mp3",
                "A:ALBUM/Abbey%20Road",
                "object.item.audioItem.musicTrack",
            ),
        ]
    return None


async def test_build_item_response(
    hass: HomeAssistant,
    soco_factory: SoCoMockFactory,
    async_autosetup_sonos,
    soco,
    discover,
) -> None:
    """Test building a browse item response."""
    soco_mock = soco_factory.mock_list.get("192.168.42.2")
    soco_mock.music_library.browse_by_idstring = mock_browse_by_idstring
    browse_item: BrowseMedia = build_item_response(
        soco_mock.music_library,
        {"search_type": MediaType.ALBUM, "idstring": "A:ALBUM/Abbey%20Road"},
        partial(
            get_thumbnail_url_full,
            soco_mock.music_library,
            True,
            None,
        ),
    )
    assert browse_item.title == "Abbey Road"
    assert browse_item.media_class == MediaClass.ALBUM
    assert browse_item.media_content_id == "A:ALBUM/Abbey%20Road"
    assert len(browse_item.children) == 2
    assert browse_item.children[0].media_class == MediaClass.TRACK
    assert browse_item.children[0].title == "Come Together"
    assert (
        browse_item.children[0].media_content_id
        == "x-file-cifs://192.168.42.10/music/The%20Beatles/Abbey%20Road/01%20Come%20Together.mp3"
    )
    assert browse_item.children[1].media_class == MediaClass.TRACK
    assert browse_item.children[1].title == "Something"
    assert (
        browse_item.children[1].media_content_id
        == "x-file-cifs://192.168.42.10/music/The%20Beatles/Abbey%20Road/03%20Something.mp3"
    )


async def test_browse_media_root(
    hass: HomeAssistant,
    soco_factory: SoCoMockFactory,
    async_autosetup_sonos,
    soco,
    discover,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the async_browse_media method."""

    client = await hass_ws_client()
    await client.send_json(
        {
            "id": 1,
            "type": "media_player/browse_media",
            "entity_id": "media_player.zone_a",
        }
    )
    response = await client.receive_json()
    assert response["success"]
    expected_children = [
        {
            "title": "Favorites",
            "media_class": "directory",
            "media_content_type": "favorites",
            "media_content_id": "",
            "can_play": False,
            "can_expand": True,
            "thumbnail": "https://brands.home-assistant.io/_/sonos/logo.png",
            "children_media_class": None,
        },
        {
            "title": "Music Library",
            "media_class": "directory",
            "media_content_type": "library",
            "media_content_id": "",
            "can_play": False,
            "can_expand": True,
            "thumbnail": "https://brands.home-assistant.io/_/sonos/logo.png",
            "children_media_class": None,
        },
    ]
    assert response["result"]["children"] == unordered(expected_children)


async def test_browse_media_library(
    hass: HomeAssistant,
    soco_factory: SoCoMockFactory,
    async_autosetup_sonos,
    soco,
    discover,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the async_browse_media method."""

    client = await hass_ws_client()
    await client.send_json(
        {
            "id": 1,
            "type": "media_player/browse_media",
            "entity_id": "media_player.zone_a",
            "media_content_id": "",
            "media_content_type": "library",
        }
    )
    response = await client.receive_json()
    assert response["success"]
    expected_children = [
        {
            "title": "Contributing Artists",
            "media_class": "contributing_artist",
            "media_content_type": "contributing_artist",
            "media_content_id": "A:ARTIST",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Artists",
            "media_class": "artist",
            "media_content_type": "artist",
            "media_content_id": "A:ALBUMARTIST",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Albums",
            "media_class": "album",
            "media_content_type": "album",
            "media_content_id": "A:ALBUM",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Genres",
            "media_class": "genre",
            "media_content_type": "genre",
            "media_content_id": "A:GENRE",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Composers",
            "media_class": "composer",
            "media_content_type": "composer",
            "media_content_id": "A:COMPOSER",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Tracks",
            "media_class": "track",
            "media_content_type": "track",
            "media_content_id": "A:TRACKS",
            "can_play": False,
            "can_expand": False,
            "thumbnail": None,
            "children_media_class": None,
        },
        {
            "title": "Playlists",
            "media_class": "playlist",
            "media_content_type": "playlist",
            "media_content_id": "A:PLAYLISTS",
            "can_play": False,
            "can_expand": True,
            "thumbnail": None,
            "children_media_class": None,
        },
    ]

    assert response["result"]["children"] == unordered(expected_children)


async def test_browse_media_library_albums(
    hass: HomeAssistant,
    soco_factory: SoCoMockFactory,
    async_autosetup_sonos,
    soco,
    discover,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the async_browse_media method."""
    soco_mock = soco_factory.mock_list.get("192.168.42.2")

    client = await hass_ws_client()
    await client.send_json(
        {
            "id": 1,
            "type": "media_player/browse_media",
            "entity_id": "media_player.zone_a",
            "media_content_id": "A:ALBUM",
            "media_content_type": "album",
        }
    )
    response = await client.receive_json()
    assert response["success"]
    expected_children = [
        {
            "title": "A Hard Day's Night",
            "media_class": "album",
            "media_content_type": "album",
            "media_content_id": "A:ALBUM/A%20Hard%20Day's%20Night",
            "can_play": True,
            "can_expand": True,
            "thumbnail": "http://192.168.42.2:1400/getaa?u=x-file-cifs://192.168.42.100/music/The%20Beatles/A%20Hard%20Day's%20Night/01%20A%20Hard%20Day's%20Night%201.m4a&v=53",
            "children_media_class": None,
        },
        {
            "title": "Abbey Road",
            "media_class": "album",
            "media_content_type": "album",
            "media_content_id": "A:ALBUM/Abbey%20Road",
            "can_play": True,
            "can_expand": True,
            "thumbnail": "http://192.168.42.2:1400/getaa?u=x-file-cifs://192.168.42.100/music/The%20Beatles/AbbeyA%20Road/01%20Come%20Together.m4a&v=53",
            "children_media_class": None,
        },
        {
            "title": "Between Good And Evil",
            "media_class": "album",
            "media_content_type": "album",
            "media_content_id": "A:ALBUM/Between%20Good%20And%20Evil",
            "can_play": True,
            "can_expand": True,
            "thumbnail": "http://192.168.42.2:1400/getaa?u=x-file-cifs://192.168.42.100/music/Santana/A%20Between%20Good%20And%20Evil/02%20A%20Persuasion.m4a&v=53",
            "children_media_class": None,
        },
    ]

    assert response["result"]["children"] == unordered(expected_children)
    assert soco_mock.music_library.browse_by_idstring.call_count == 1
