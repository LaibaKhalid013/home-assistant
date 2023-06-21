"""Support for MQTT images."""
from __future__ import annotations

from base64 import b64decode
import binascii
from collections.abc import Callable
import functools
import logging
import ssl
from typing import Any

import httpx
import voluptuous as vol

from homeassistant.components import image
from homeassistant.components.image import (
    ATTR_IMAGE_LAST_UPDATED,
    DEFAULT_CONTENT_TYPE,
    ImageEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.service_info.mqtt import ReceivePayloadType
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from . import subscription
from .config import MQTT_BASE_SCHEMA
from .const import CONF_ENCODING, CONF_QOS, CONF_TOPIC
from .debug_info import log_messages
from .mixins import MQTT_ENTITY_COMMON_SCHEMA, MqttEntity, async_setup_entry_helper
from .models import MessageCallbackType, MqttValueTemplate, ReceiveMessage
from .util import get_mqtt_data, valid_subscribe_topic

_LOGGER = logging.getLogger(__name__)

CONF_CONTENT_TYPE = "content_type"
CONF_IMAGE_ENCODING = "image_encoding"
CONF_FROM_URL_TOPIC = "from_url_topic"

DEFAULT_NAME = "MQTT Image"

MQTT_IMAGE_ATTRIBUTES_BLOCKED = frozenset({ATTR_IMAGE_LAST_UPDATED})


def validate_content_type(content_type: str) -> str:
    """Validate the config type is an image."""
    if content_type.split("/")[0] != "image":
        raise vol.Invalid(f"Content type {content_type} is not valid")
    return content_type


PLATFORM_SCHEMA_BASE = MQTT_BASE_SCHEMA.extend(
    {
        vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): vol.All(
            cv.string, validate_content_type
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Exclusive(CONF_FROM_URL_TOPIC, "image_url"): valid_subscribe_topic,
        vol.Exclusive(CONF_TOPIC, "url_url"): valid_subscribe_topic,
        vol.Optional(CONF_IMAGE_ENCODING): "b64",
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
).extend(MQTT_ENTITY_COMMON_SCHEMA.schema)

PLATFORM_SCHEMA_MODERN = vol.All(
    PLATFORM_SCHEMA_BASE.schema,
)

DISCOVERY_SCHEMA = PLATFORM_SCHEMA_BASE.extend({}, extra=vol.REMOVE_EXTRA)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MQTT image through YAML and through MQTT discovery."""
    setup = functools.partial(
        _async_setup_entity, hass, async_add_entities, config_entry=config_entry
    )
    await async_setup_entry_helper(hass, image.DOMAIN, setup, DISCOVERY_SCHEMA)


async def _async_setup_entity(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config: ConfigType,
    config_entry: ConfigEntry,
    discovery_data: DiscoveryInfoType | None = None,
) -> None:
    """Set up the MQTT Image."""
    async_add_entities([MqttImage(hass, config, config_entry, discovery_data)])


class MqttImage(MqttEntity, ImageEntity):
    """representation of a MQTT image."""

    _entity_id_format: str = image.ENTITY_ID_FORMAT
    _attributes_extra_blocked: frozenset[str] = MQTT_IMAGE_ATTRIBUTES_BLOCKED
    _last_image: bytes | None = None
    _client: httpx.AsyncClient
    _template: Callable[[ReceivePayloadType], ReceivePayloadType]
    _topic: dict[str, Any]

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigType,
        config_entry: ConfigEntry,
        discovery_data: DiscoveryInfoType | None,
    ) -> None:
        """Initialize the MQTT Image."""
        self._client = get_async_client(hass)
        ImageEntity.__init__(self)
        MqttEntity.__init__(self, hass, config, config_entry, discovery_data)

    @staticmethod
    def config_schema() -> vol.Schema:
        """Return the config schema."""
        return DISCOVERY_SCHEMA

    def _setup_from_config(self, config: ConfigType) -> None:
        """(Re)Setup the entity."""
        self._topic = {
            key: config.get(key)
            for key in (
                CONF_TOPIC,
                CONF_FROM_URL_TOPIC,
            )
        }
        if CONF_TOPIC in config:
            self._attr_content_type = config[CONF_CONTENT_TYPE]
        self._template = MqttValueTemplate(
            config.get(CONF_VALUE_TEMPLATE), entity=self
        ).async_render_with_possible_json_value

    async def _async_load_image(self, url: str) -> None:
        try:
            response = await self._client.request("GET", url)
        except (httpx.TimeoutException, httpx.RequestError, ssl.SSLError) as ex:
            _LOGGER.warning("Connection failed to url %s files: %s", url, ex)
            return

        try:
            content_type = validate_content_type(response.headers["content-type"])
        except vol.Invalid as err:
            _LOGGER.error(
                "Content is not a valid image, url: %s, content_type: %s, %s",
                url,
                response.headers["content-type"],
                err,
            )
            return
        self._attr_content_type = content_type
        self._last_image = response.content
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    def _prepare_subscribe_topics(self) -> None:
        """(Re)Subscribe to topics."""

        topics: dict[str, Any] = {}

        def add_subscribe_topic(topic: str, msg_callback: MessageCallbackType) -> bool:
            """Add a topic to subscribe to."""
            if has_topic := self._topic[topic] is not None:
                topics[topic] = {
                    "topic": self._topic[topic],
                    "msg_callback": msg_callback,
                    "qos": self._config[CONF_QOS],
                    "encoding": self._config[CONF_ENCODING] or None,
                }
            return has_topic

        @callback
        @log_messages(self.hass, self.entity_id)
        def image_data_received(msg: ReceiveMessage) -> None:
            """Handle new MQTT messages."""
            try:
                if CONF_IMAGE_ENCODING in self._config:
                    self._last_image = b64decode(msg.payload)
                else:
                    assert isinstance(msg.payload, bytes)
                    self._last_image = msg.payload
            except (binascii.Error, ValueError, AssertionError) as err:
                _LOGGER.error(
                    "Error processing image data received at topic %s: %s",
                    msg.topic,
                    err,
                )
                return
            self._attr_image_last_updated = dt_util.utcnow()
            get_mqtt_data(self.hass).state_write_requests.write_state_request(self)

        add_subscribe_topic(CONF_TOPIC, image_data_received)

        @callback
        @log_messages(self.hass, self.entity_id)
        def image_from_url_request_received(msg: ReceiveMessage) -> None:
            """Handle new MQTT messages."""

            try:
                url = cv.url(self._template(msg.payload))
            except vol.Invalid:
                _LOGGER.error(
                    "Invalid image URL '%s' received at topic %s",
                    msg.payload,
                    msg.topic,
                )
                return
            self.hass.async_create_task(self._async_load_image(url))

        add_subscribe_topic(CONF_FROM_URL_TOPIC, image_from_url_request_received)

        self._sub_state = subscription.async_prepare_subscribe_topics(
            self.hass, self._sub_state, topics
        )

    async def _subscribe_topics(self) -> None:
        """(Re)Subscribe to topics."""
        await subscription.async_subscribe_topics(self.hass, self._sub_state)

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        return self._last_image
