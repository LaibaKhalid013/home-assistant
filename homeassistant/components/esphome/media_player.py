"""Support for ESPHome media players."""

from __future__ import annotations

from typing import Any

from aioesphomeapi import (
    EntityInfo,
    MediaPlayerCommand,
    MediaPlayerEntityState,
    MediaPlayerInfo,
    MediaPlayerState as EspMediaPlayerState,
)

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_ENQUEUE,
    BrowseMedia,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
    RepeatMode,
    MediaPlayerEnqueue,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_EXTRA,
    vol,
    cv,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import (
    EsphomeEntity,
    convert_api_error_ha_error,
    esphome_state_property,
    platform_async_setup_entry,
)
from .enum_mapper import EsphomeEnumMapper


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up esphome media players based on a config entry."""
    await platform_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        info_type=MediaPlayerInfo,
        entity_type=EsphomeMediaPlayer,
        state_type=MediaPlayerEntityState,
    )


_STATES: EsphomeEnumMapper[EspMediaPlayerState, MediaPlayerState] = EsphomeEnumMapper(
    {
        EspMediaPlayerState.OFF: MediaPlayerState.OFF,
        EspMediaPlayerState.ON: MediaPlayerState.ON,
        EspMediaPlayerState.IDLE: MediaPlayerState.IDLE,
        EspMediaPlayerState.PLAYING: MediaPlayerState.PLAYING,
        EspMediaPlayerState.PAUSED: MediaPlayerState.PAUSED,
        EspMediaPlayerState.ANNOUNCING: 6,
        #EspMediaPlayerState.ANNOUNCING: MediaPlayerState.ANNOUNCING,
    }
)


class EsphomeMediaPlayer(
    EsphomeEntity[MediaPlayerInfo, MediaPlayerEntityState], MediaPlayerEntity
):
    """A media player implementation for esphome."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    @callback
    def _on_static_info_update(self, static_info: EntityInfo) -> None:
        """Set attrs from static info."""
        super()._on_static_info_update(static_info)
        flags = (
            MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.MEDIA_ANNOUNCE
        )
        if self._static_info.supports_grouping:
            flags |= MediaPlayerEntityFeature.GROUPING
        
        if self._static_info.supports_pause:
            flags |= MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.PLAY
        
        if self._static_info.supports_next_previous_track:
            flags |= MediaPlayerEntityFeature.NEXT_TRACK | MediaPlayerEntityFeature.PREVIOUS_TRACK | MediaPlayerEntityFeature.CLEAR_PLAYLIST
            flags |= MediaPlayerEntityFeature.MEDIA_ENQUEUE | MediaPlayerEntityFeature.REPEAT_SET | MediaPlayerEntityFeature.SHUFFLE_SET

        if self._static_info.supports_turn_off_on:
            flags |= MediaPlayerEntityFeature.TURN_OFF | MediaPlayerEntityFeature.TURN_ON
        self._attr_supported_features = flags

    @callback
    def _on_state_update(self) -> None:
        """Call when state changed."""
        super()._on_state_update()
        self._attr_media_position_updated_at = dt.utcnow()
        
    @property
    @esphome_state_property
    def state(self) -> MediaPlayerState | None:
        """Return current state."""
        return _STATES.from_esphome(self._state.state)

    @property
    @esphome_state_property
    def is_volume_muted(self) -> bool:
        """Return true if volume is muted."""
        return self._state.muted

    @property
    @esphome_state_property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        return self._state.volume

    @property
    @esphome_state_property
    def repeat(self) -> RepeatMode:
        """Repeat the song or playlist"""
        return self._state.repeat

    @property
    @esphome_state_property
    def shuffle(self) -> bool:
        """Return true if set is shuffled."""
        return self._state.shuffle

    @property
    @esphome_state_property
    def media_artist(self) -> str:
        """artist"""
        return self._state.artist

    @property
    @esphome_state_property
    def media_album_artist(self) -> str:
        """artist"""
        if len(self._state.artist) > 0:
            return self._state.artist
        else:
            return self._attr_media_artist

    @property
    @esphome_state_property
    def media_album_name(self) -> str:
        """album"""
        if len(self._state.album) > 0:
            return self._state.album
        else:
            return self._attr_media_album_name

    @property
    @esphome_state_property
    def media_title(self) -> str:
        """title"""
        if len(self._state.title) > 0:
            if len(self._state.artist) > 0:
                return self._state.artist + ': ' + self._state.title
            else:
                return self._state.title
        else:
            return self._attr_media_title

    @property
    @esphome_state_property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""
        if self._state.duration == 0:
            return None
        else:
            return self._state.duration

    @property
    @esphome_state_property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""
        if self._state.duration == 0:
            return None
        else:
            return self._state.position
    
    @convert_api_error_ha_error
    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Send the play command with media url to the media player."""
        if media_id != 'listen' or media_id != 'unlisten':
            if media_source.is_media_source_id(media_id):
                sourced_media = await media_source.async_resolve_media(
                    self.hass, media_id, self.entity_id
                )
                media_id = sourced_media.url

            media_id = async_process_play_media_url(self.hass, media_id)

        has_mrm = False
        announcement = False
        enqueue = MediaPlayerEnqueue.REPLACE
        for key, value in kwargs.items():
            if key == ATTR_MEDIA_ANNOUNCE:
                announcement = value
            elif key == ATTR_MEDIA_ENQUEUE:
                enqueue = value
            elif key == ATTR_MEDIA_EXTRA:
                for k,v in value.items():
                    if k == 'mrm':
                        has_mrm = True
                        mrm = v
        if has_mrm:
            self._client.media_player_command(
                self._key, media_url=media_id, announcement=announcement, enqueue=enqueue, mrm=mrm
            )
        else:
            self._client.media_player_command(
                self._key, media_url=media_id, announcement=announcement, enqueue=enqueue, 
            )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    @convert_api_error_ha_error
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        self._client.media_player_command(self._key, volume=volume)

    @convert_api_error_ha_error
    async def async_media_pause(self) -> None:
        """Send pause command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.PAUSE)

    @convert_api_error_ha_error
    async def async_media_play(self) -> None:
        """Send play command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.PLAY)

    @convert_api_error_ha_error
    async def async_media_stop(self) -> None:
        """Send stop command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.STOP)

    @convert_api_error_ha_error
    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        self._client.media_player_command(
            self._key,
            command=MediaPlayerCommand.MUTE if mute else MediaPlayerCommand.UNMUTE,
        )

    @convert_api_error_ha_error
    async def async_media_next_track(self) -> None:
        """Send next track command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.NEXT_TRACK)

    @convert_api_error_ha_error
    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.PREVIOUS_TRACK)

    @convert_api_error_ha_error
    async def async_clear_playlist(self) -> None:
        """Send clear playlist command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.CLEAR_PLAYLIST)

    @convert_api_error_ha_error
    async def async_set_shuffle(self, shuffle: str) -> None:
        """Send set shuffle command."""
        self._client.media_player_command(
            self._key,
            command=MediaPlayerCommand.SHUFFLE if shuffle else MediaPlayerCommand.UNSHUFFLE,
        )

    @convert_api_error_ha_error
    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Send repeat set command."""
        repeatCmd = MediaPlayerCommand.REPEAT_OFF
        if repeat == RepeatMode.ONE:
            repeatCmd = MediaPlayerCommand.REPEAT_ONE
        elif repeat == RepeatMode.ALL:
            repeatCmd = MediaPlayerCommand.REPEAT_ALL
            
        self._client.media_player_command(self._key, command=repeatCmd)

    @convert_api_error_ha_error
    async def async_turn_on(self) -> None:
        """Send turn on command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.TURN_ON)

    @convert_api_error_ha_error
    async def async_turn_off(self) -> None:
        """Send turn off command."""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.TURN_OFF)

    @convert_api_error_ha_error
    async def async_join_players(self, group_members: list[str]) -> None:
        """Self will be leader of group and group_members who will be followers"""
        gms = ""
        for gm in group_members:
            gms = gms + gm + ","
        self._client.media_player_command(self._key, group_members=gms, command=MediaPlayerCommand.JOIN)

    @convert_api_error_ha_error
    async def async_unjoin_player(self) -> None:
        """Remove knowledge of self ability to publish and remove group_members as subscribers"""
        self._client.media_player_command(self._key, command=MediaPlayerCommand.UNJOIN)