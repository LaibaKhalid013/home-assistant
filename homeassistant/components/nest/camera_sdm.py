"""Support for Google Nest SDM Cameras."""
from __future__ import annotations

from collections.abc import Callable
import datetime
import logging
from pathlib import Path

from google_nest_sdm.camera_traits import (
    CameraEventImageTrait,
    CameraImageTrait,
    CameraLiveStreamTrait,
    RtspStream,
    StreamingProtocol,
)
from google_nest_sdm.device import Device
from google_nest_sdm.event_media import EventMedia
from google_nest_sdm.exceptions import ApiException
from haffmpeg.tools import IMAGE_JPEG

from homeassistant.components.camera import SUPPORT_STREAM, Camera
from homeassistant.components.camera.const import STREAM_TYPE_HLS, STREAM_TYPE_WEB_RTC
from homeassistant.components.ffmpeg import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, PlatformNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

from .const import DATA_SUBSCRIBER, DOMAIN
from .device_info import NestDeviceInfo

_LOGGER = logging.getLogger(__name__)

PLACEHOLDER = Path(__file__).parent / "placeholder.png"

# Used to schedule an alarm to refresh the stream before expiration
STREAM_EXPIRATION_BUFFER = datetime.timedelta(seconds=30)


async def async_setup_sdm_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the cameras."""

    subscriber = hass.data[DOMAIN][DATA_SUBSCRIBER]
    try:
        device_manager = await subscriber.async_get_device_manager()
    except ApiException as err:
        raise PlatformNotReady from err

    # Fetch initial data so we have data when entities subscribe.

    entities = []
    for device in device_manager.devices.values():
        if (
            CameraImageTrait.NAME in device.traits
            or CameraLiveStreamTrait.NAME in device.traits
        ):
            entities.append(NestCamera(device))
    async_add_entities(entities)


class NestCamera(Camera):
    """Devices that support cameras."""

    def __init__(self, device: Device) -> None:
        """Initialize the camera."""
        super().__init__()
        self._device = device
        self._device_info = NestDeviceInfo(device)
        self._stream: RtspStream | None = None
        self._stream_refresh_unsub: Callable[[], None] | None = None
        self._attr_is_streaming = CameraLiveStreamTrait.NAME in self._device.traits
        self._placeholder_image: bytes | None = None

    @property
    def should_poll(self) -> bool:
        """Disable polling since entities have state pushed via pubsub."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        # The API "name" field is a unique device identifier.
        return f"{self._device.name}-camera"

    @property
    def name(self) -> str | None:
        """Return the name of the camera."""
        return self._device_info.device_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return self._device_info.device_info

    @property
    def brand(self) -> str | None:
        """Return the camera brand."""
        return self._device_info.device_brand

    @property
    def model(self) -> str | None:
        """Return the camera model."""
        return self._device_info.device_model

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        supported_features = 0
        if CameraLiveStreamTrait.NAME in self._device.traits:
            supported_features |= SUPPORT_STREAM
        return supported_features

    @property
    def frontend_stream_type(self) -> str | None:
        """Return the type of stream supported by this camera."""
        if CameraLiveStreamTrait.NAME not in self._device.traits:
            return None
        trait = self._device.traits[CameraLiveStreamTrait.NAME]
        if StreamingProtocol.WEB_RTC in trait.supported_protocols:
            return STREAM_TYPE_WEB_RTC
        return STREAM_TYPE_HLS

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        if not self.supported_features & SUPPORT_STREAM:
            return None
        if CameraLiveStreamTrait.NAME not in self._device.traits:
            return None
        trait = self._device.traits[CameraLiveStreamTrait.NAME]
        if StreamingProtocol.RTSP not in trait.supported_protocols:
            return None
        if not self._stream:
            _LOGGER.debug("Fetching stream url")
            try:
                self._stream = await trait.generate_rtsp_stream()
            except ApiException as err:
                raise HomeAssistantError(f"Nest API error: {err}") from err
            self._schedule_stream_refresh()
        assert self._stream
        if self._stream.expires_at < utcnow():
            _LOGGER.warning("Stream already expired")
        return self._stream.rtsp_stream_url

    def _schedule_stream_refresh(self) -> None:
        """Schedules an alarm to refresh the stream url before expiration."""
        assert self._stream
        _LOGGER.debug("New stream url expires at %s", self._stream.expires_at)
        refresh_time = self._stream.expires_at - STREAM_EXPIRATION_BUFFER
        # Schedule an alarm to extend the stream
        if self._stream_refresh_unsub is not None:
            self._stream_refresh_unsub()

        self._stream_refresh_unsub = async_track_point_in_utc_time(
            self.hass,
            self._handle_stream_refresh,
            refresh_time,
        )

    async def _handle_stream_refresh(self, now: datetime.datetime) -> None:
        """Alarm that fires to check if the stream should be refreshed."""
        if not self._stream:
            return
        _LOGGER.debug("Extending stream url")
        try:
            self._stream = await self._stream.extend_rtsp_stream()
        except ApiException as err:
            _LOGGER.debug("Failed to extend stream: %s", err)
            # Next attempt to catch a url will get a new one
            self._stream = None
            if self.stream:
                self.stream.stop()
                self.stream = None
            return
        # Update the stream worker with the latest valid url
        if self.stream:
            self.stream.update_source(self._stream.rtsp_stream_url)
        self._schedule_stream_refresh()

    async def async_will_remove_from_hass(self) -> None:
        """Invalidates the RTSP token when unloaded."""
        if self._stream:
            _LOGGER.debug("Invalidating stream")
            await self._stream.stop_rtsp_stream()
        if self._stream_refresh_unsub:
            self._stream_refresh_unsub()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to register update signal handler."""
        self.async_on_remove(
            self._device.add_update_listener(self.async_write_ha_state)
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        if CameraEventImageTrait.NAME in self._device.traits:
            # Returns the snapshot of the last event for ~30 seconds after the event
            event_media: EventMedia | None = None
            try:
                event_media = (
                    await self._device.event_media_manager.get_active_event_media()
                )
            except ApiException as err:
                _LOGGER.debug("Failure while getting image for event: %s", err)
            if event_media:
                return event_media.media.contents
        # Fetch still image from the live stream
        stream_url = await self.stream_source()
        if not stream_url:
            if self.frontend_stream_type != STREAM_TYPE_WEB_RTC:
                return None
            # Nest Web RTC cams only have image previews for events, and not
            # for "now" by design to save batter, and need a placeholder.
            if not self._placeholder_image:
                self._placeholder_image = await self.hass.async_add_executor_job(
                    PLACEHOLDER.read_bytes
                )
            return self._placeholder_image
        return await async_get_image(self.hass, stream_url, output_format=IMAGE_JPEG)

    async def async_handle_web_rtc_offer(self, offer_sdp: str) -> str:
        """Return the source of the stream."""
        trait: CameraLiveStreamTrait = self._device.traits[CameraLiveStreamTrait.NAME]
        try:
            stream = await trait.generate_web_rtc_stream(offer_sdp)
        except ApiException as err:
            raise HomeAssistantError(f"Nest API error: {err}") from err
        return stream.answer_sdp
