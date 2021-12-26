"""The tests for the signal_messenger platform."""
import base64
import json
import logging
import os
import tempfile
from unittest.mock import patch

import pytest

from homeassistant.setup import async_setup_component

from tests.components.signal_messenger.conftest import (
    CONTENT,
    MESSAGE,
    NUMBER_FROM,
    NUMBERS_TO,
    SIGNAL_SEND_PATH_SUFIX,
    URL_ATTACHMENT,
)

BASE_COMPONENT = "notify"


async def test_signal_messenger_init(hass):
    """Test that service loads successfully."""
    config = {
        BASE_COMPONENT: {
            "name": "test",
            "platform": "signal_messenger",
            "url": "http://127.0.0.1:8080",
            "number": NUMBER_FROM,
            "recipients": NUMBERS_TO,
        }
    }

    with patch("pysignalclirestapi.SignalCliRestApi.send_message", return_value=None):
        assert await async_setup_component(hass, BASE_COMPONENT, config)
        await hass.async_block_till_done()

        assert hass.services.has_service(BASE_COMPONENT, "test")


def test_send_message(signal_notification_service, signal_requests_mock, caplog):
    """Test send message."""
    with caplog.at_level(
        logging.DEBUG, logger="homeassistant.components.signal_messenger.notify"
    ):
        signal_notification_service.send_message(MESSAGE)
    assert "Sending signal message" in caplog.text
    assert signal_requests_mock.called
    assert signal_requests_mock.call_count == 2
    assert_sending_requests(signal_requests_mock)


def test_send_message_should_show_deprecation_warning(
    signal_notification_service, signal_requests_mock, caplog
):
    """Test send message should show deprecation warning."""
    with caplog.at_level(
        logging.WARNING, logger="homeassistant.components.signal_messenger.notify"
    ):
        send_message_with_attachment(signal_notification_service, True)

    assert (
        "The 'attachment' option is deprecated, please replace it with 'attachments'. This option will become invalid in version 0.108"
        in caplog.text
    )
    assert signal_requests_mock.called
    assert signal_requests_mock.call_count == 2
    assert_sending_requests(signal_requests_mock, 1)


def test_send_message_with_attachment(
    signal_notification_service, signal_requests_mock, caplog
):
    """Test send message with attachment."""
    with caplog.at_level(
        logging.DEBUG, logger="homeassistant.components.signal_messenger.notify"
    ):
        send_message_with_attachment(signal_notification_service, False)

    assert "Sending signal message" in caplog.text
    assert signal_requests_mock.called
    assert signal_requests_mock.call_count == 2
    assert_sending_requests(signal_requests_mock, 1)


def send_message_with_attachment(signal_notification_service, deprecated=False):
    """Send message with attachment."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".png", prefix=os.path.basename(__file__)
    ) as tf:
        tf.write("attachment_data")
        data = {"attachment": tf.name} if deprecated else {"attachments": [tf.name]}
        signal_notification_service.send_message(MESSAGE, **{"data": data})


def test_send_message_with_attachment_as_url(
    signal_notification_service, signal_attachment_requests_mock, caplog
):
    """Test send message with attachment as URL."""
    with caplog.at_level(
        logging.DEBUG, logger="homeassistant.components.signal_messenger.notify"
    ):
        send_message_with_attachment_as_url(signal_notification_service)

    assert "Sending signal message" in caplog.text
    assert signal_attachment_requests_mock.called
    assert signal_attachment_requests_mock.call_count == 3
    assert_sending_requests(signal_attachment_requests_mock, 1)


def test_send_message_with_large_attachment_as_url(
    signal_notification_service, signal_large_attachment_requests_mock, caplog
):
    """Test send message with large attachment as URL throws error."""
    with caplog.at_level(
        logging.DEBUG, logger="homeassistant.components.signal_messenger.notify"
    ):
        with pytest.raises(ValueError) as exc:
            send_message_with_attachment_as_url(signal_notification_service)

    assert "Sending signal message" in caplog.text
    assert signal_large_attachment_requests_mock.called
    assert signal_large_attachment_requests_mock.call_count == 1
    assert "Attachment too large" in str(exc.value)


def send_message_with_attachment_as_url(signal_notification_service):
    """Send message with attachment from URL."""
    data = {"urls": [URL_ATTACHMENT]}
    signal_notification_service.send_message(MESSAGE, **{"data": data})


def assert_sending_requests(signal_requests_mock, attachments_num=0):
    """Assert message was send with correct parameters."""
    send_request = signal_requests_mock.request_history[-1]
    assert send_request.path == SIGNAL_SEND_PATH_SUFIX

    body_request = json.loads(send_request.text)
    assert body_request["message"] == MESSAGE
    assert body_request["number"] == NUMBER_FROM
    assert body_request["recipients"] == NUMBERS_TO
    assert len(body_request["base64_attachments"]) == attachments_num

    for attachment in body_request["base64_attachments"]:
        if len(attachment) > 0:
            assert base64.b64decode(attachment) == CONTENT
