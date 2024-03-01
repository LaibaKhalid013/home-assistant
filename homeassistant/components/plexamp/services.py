"""Handles communication with Plexamp services."""

import logging
import defusedxml.ElementTree as ET
import requests

from homeassistant.components.media_player import MediaPlayerState

from .const import NUMBER_TO_REPEAT_MODE
from .utils import replace_ip_prefix

_LOGGER = logging.getLogger(__name__)


class PlexampService:
    _plex_token: str
    _plex_identifier: str
    _plex_ip_address: str
    _host: str
    _device_name: str
    _command_id: int

    def __init__(self, plex_token: str | None, plex_identifier: str | None, plex_ip_address: str | None, host: str,
                 device_name: str) -> None:
        self._plex_token = plex_token
        self._plex_identifier = plex_identifier
        self._plex_ip_address = plex_ip_address
        self._host = host
        self._device_name = device_name
        self._command_id = 1

        _LOGGER.debug("Starting PlexampService for: %s", device_name)

    def send_playback_command(self, action: str) -> None:
        """Send a command to the player."""

        headers = {
            "X-Plex-Token": self._plex_token,
            "X-Plex-Target-Client-Identifier": self._plex_identifier
        }
        url = f"{self._host}/player/playback/{action}"
        _LOGGER.debug("Sending playback command to %s: %s", self._device_name, url)
        try:
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
        except Exception as e:
            _LOGGER.error("Failed to send command %s in %s: %s", action, self._device_name, e)

    def send_set_parameter_command(self, parameters: str) -> None:
        """Send a parameter command to the player."""

        headers = {
            "X-Plex-Token": self._plex_token,
            "X-Plex-Target-Client-Identifier": self._plex_identifier
        }

        url = f"{self._host}/player/playback/setParameters?{parameters}"
        _LOGGER.debug("Sending parameter command to %s: %s", self._device_name, url)
        try:
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

        except Exception as e:
            _LOGGER.error(
                "Failed to set parameter %s in %s: %s",
                parameters,
                self._device_name,
                e,
            )

    def get_device_information(self, poll_wait=0) -> dict:
        """Get device information from Plexamp.

        Returns:
            Dict[str, Union[str, bool, float, None]]: A dictionary containing the following keys:
                - 'state' (str): The state of the media player.
                - 'shuffle' (bool): Whether shuffle mode is enabled.
                - 'volume_level' (float): The current volume level.
                - 'volume_step' (float): The step size for volume adjustments.
                - 'repeat' (str or None): The repeat mode.
                - 'thumb' (str or None): The URL of the thumbnail image.
                - 'title' (str or None): The title of the currently playing media.
                - 'parent_title' (str or None): The title of the parent media.
                - 'grandparent_title' (str or None): The title of the grandparent media.

        """

        base_url = f"{self._host}/player/timeline/poll"
        url = f"{base_url}?wait={poll_wait}&includeMetadata=1&commandID={self._command_id}&type=music"
        _LOGGER.debug("Updating device: %s", self._device_name)

        device_information = {
            "state": MediaPlayerState.IDLE,
            "shuffle": False,
            "volume_level": 1.0,
            "volume_step": 0.1,
            "repeat": NUMBER_TO_REPEAT_MODE.get("0"),
            "thumb": "",
            "title": "",
            "parent_title": "",
            "grandparent_title": ""
        }

        try:
            headers = {
                "X-Plex-Token": self._plex_token,
                "X-Plex-Target-Client-Identifier": self._plex_identifier,
                "Accept": "application/json"
            }

            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            self._command_id = self._command_id + 1
            content = response.content
            root = ET.fromstring(content)

            for timeline in root.findall("Timeline"):
                if timeline.get("itemType") == "music":
                    status = timeline.get("state", MediaPlayerState.IDLE)
                    _LOGGER.debug("status %s device: %s", status, self._device_name)
                    device_information["state"] = {
                        "playing": MediaPlayerState.PLAYING,
                        "paused": MediaPlayerState.PAUSED,
                    }.get(status)

                    device_information["shuffle"] = timeline.get("shuffle", 0) != "0"
                    device_information["volume"] = float(timeline.get("volume", 1.0)) / 100

                    repeat_mode_value = timeline.get("repeat", 0)
                    device_information["repeat"] = NUMBER_TO_REPEAT_MODE.get(repeat_mode_value)

                    # If the user didn't provide the token, we can't get queue info and metadata
                    if not self._plex_token or not self._plex_ip_address:
                        return device_information

                    # Since we get the docker internal url, we need to use the user provided plex url
                    formatted_ip_address = self._plex_ip_address.replace(".", "-")
                    play_queue = timeline.get("containerKey")

                    if not play_queue:
                        break

                    address = replace_ip_prefix(timeline.get("address", ""), formatted_ip_address)
                    protocol = timeline.get("protocol")
                    port = timeline.get("port")
                    metadata_base_url = f"{protocol}://{address}:{port}"
                    play_queue_url = f"{metadata_base_url}{play_queue}"

                    try:
                        queue_data = requests.get(play_queue_url, timeout=10, headers=headers)
                        queue = queue_data.json() if queue_data.status_code == 200 else None

                        if not queue:
                            break
                        # Get the currently playing ID
                        currently_playing_id = queue.get("MediaContainer", {}).get("playQueueSelectedItemID")

                        if currently_playing_id is not None:
                            # Get the Metadata array
                            metadata = queue.get("MediaContainer", {}).get("Metadata", [])

                            currently_playing_metadata = next(
                                (item for item in metadata if item.get('playQueueItemID') == currently_playing_id),
                                None)

                            thumb_size = "width=300&height=300"
                            thumb_url = currently_playing_metadata.get("thumb")
                            thumb_parameters = f"url={thumb_url}&quality=90&format=jpeg&X-Plex-Token={self._plex_token}"

                            thumb = f"{metadata_base_url}/photo/:/transcode?{thumb_size}&{thumb_parameters}" if thumb_url else None
                            title = currently_playing_metadata.get("title")
                            parent_title = currently_playing_metadata.get("parentTitle")
                            grandparent_title = currently_playing_metadata.get("grandparentTitle")

                            device_information["title"] = title
                            device_information["thumb"] = thumb
                            device_information["parent_title"] = parent_title
                            device_information["grandparent_title"] = grandparent_title

                            return device_information

                        return device_information


                    except Exception as e:
                        _LOGGER.error("Couldn't update medata for %s: %s. Error: %s", self._device_name, play_queue_url, e)

                    # plexamp does not support photo and video, returned by Plex
                    break
        except Exception as e:
            _LOGGER.error("Error updating device %s, errr: %s", self._device_name, e)
            return device_information

