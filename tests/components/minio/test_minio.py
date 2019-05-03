"""Tests for Minio Hass related code."""
import asyncio
import json
from unittest.mock import MagicMock, patch

from homeassistant.components.minio import QueueListener, DOMAIN, CONF_HOST, \
    CONF_PORT, CONF_ACCESS_KEY, CONF_SECRET_KEY, CONF_SECURE, CONF_LISTEN, \
    CONF_LISTEN_BUCKET
from homeassistant.const import EVENT_HOMEASSISTANT_START, \
    EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.setup import async_setup_component

from tests.components.minio.common import TEST_EVENT


async def test_minio_services(hass, caplog):
    """Test Minio services."""
    hass.config.whitelist_external_dirs = set('/tmp')

    minio_client_mock = MagicMock()

    with patch('homeassistant.components.minio.Minio') as minio_mock:
        minio_mock.return_value = minio_client_mock

        await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_HOST: 'localhost',
                    CONF_PORT: '9000',
                    CONF_ACCESS_KEY: 'abcdef',
                    CONF_SECRET_KEY: '0123456789',
                    CONF_SECURE: 'true',
                }
            }
        )

        hass.bus.fire(EVENT_HOMEASSISTANT_START)
        await hass.async_block_till_done()

        assert 'Setup of domain minio took' in caplog.text

    # Call services
    await hass.services.async_call(
        DOMAIN,
        'put',
        {
            'file_path': '/tmp/some_file',
            'key': 'some_key',
            'bucket': 'some_bucket'
        },
        blocking=True
    )
    minio_client_mock.fput_object.assert_called_with(
        'some_bucket', 'some_key', '/tmp/some_file'
    )
    minio_client_mock.reset_mock()

    await hass.services.async_call(
        DOMAIN,
        'get',
        {
            'file_path': '/tmp/some_file',
            'key': 'some_key',
            'bucket': 'some_bucket'
        },
        blocking=True
    )
    minio_client_mock.fget_object.assert_called_with(
        'some_bucket', 'some_key', '/tmp/some_file'
    )
    minio_client_mock.reset_mock()

    await hass.services.async_call(
        DOMAIN,
        'remove',
        {
            'key': 'some_key',
            'bucket': 'some_bucket'
        },
        blocking=True
    )
    minio_client_mock.remove_object.assert_called_with(
        'some_bucket', 'some_key'
    )
    minio_client_mock.reset_mock()


async def test_minio_listen(hass, caplog):
    """Test minio listen on notifications."""
    minio_client_mock = MagicMock()

    with patch('homeassistant.components.minio.Minio') as _minio_mock, \
            patch('homeassistant.components.minio.minio_helper.Minio') \
            as minio_mock:
        _minio_mock.return_value = MagicMock()
        minio_mock.return_value = minio_client_mock

        response_mock = MagicMock()
        stream_mock = MagicMock()

        response_mock.stream.return_value = stream_mock

        stream_mock.__next__.side_effect = [
            '',
            '',
            bytearray(json.dumps(TEST_EVENT), 'utf-8')
        ]

        minio_client_mock._url_open.return_value = response_mock
        minio_client_mock.presigned_get_object.return_value = 'http://url'

        events = []

        @callback
        def event_callback(event):
            """Handle event callbback."""
            events.append(event)

        hass.bus.async_listen('minio', event_callback)

        await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_HOST: 'localhost',
                    CONF_PORT: '9000',
                    CONF_ACCESS_KEY: 'abcdef',
                    CONF_SECRET_KEY: '0123456789',
                    CONF_SECURE: 'true',
                    CONF_LISTEN: [{
                        CONF_LISTEN_BUCKET: 'test'
                    }]
                }
            }
        )

        hass.bus.fire(EVENT_HOMEASSISTANT_START)
        await hass.async_block_till_done()

        assert 'Setup of domain minio took' in caplog.text

        while not events:
            await asyncio.sleep(0)

        hass.bus.fire(EVENT_HOMEASSISTANT_STOP)

        assert 1 == len(events)
        event = events[0]

        assert DOMAIN == event.event_type
        assert 's3:ObjectCreated:Put' == event.data['event_name']
        assert '5jJkTAo.jpg' == event.data['file_name']
        assert 'test' == event.data['bucket']
        assert '5jJkTAo.jpg' == event.data['key']
        assert 'http://url' == event.data['presigned_url']
        assert 0 == len(event.data['metadata'])


async def test_queue_listener():
    """Tests QueueListener firing events on Hass event bus."""
    hass = MagicMock()

    queue_listener = QueueListener(hass)
    queue_listener.start()

    queue_entry = {
        'event_name': 's3:ObjectCreated:Put',
        'bucket': 'some_bucket',
        'key': 'some_dir/some_file.jpg',
        'presigned_url': 'http://host/url?signature=secret',
        'metadata': {},
    }

    queue_listener.queue.put(queue_entry)

    queue_listener.stop()

    call_domain, call_event = hass.bus.fire.call_args[0]

    expected_event = {
        'event_name': 's3:ObjectCreated:Put',
        'file_name': 'some_file.jpg',
        'bucket': 'some_bucket',
        'key': 'some_dir/some_file.jpg',
        'presigned_url': 'http://host/url?signature=secret',
        'metadata': {},
    }

    assert DOMAIN == call_domain
    assert json.dumps(expected_event, sort_keys=True) == \
        json.dumps(call_event, sort_keys=True)
