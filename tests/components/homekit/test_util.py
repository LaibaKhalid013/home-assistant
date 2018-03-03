"""Test HomeKit util module."""
import unittest
from unittest.mock import call, patch, ANY

import voluptuous as vol

from homeassistant.core import callback
# from homeassistant.components.homekit import CONFIG_SCHEMA
from homeassistant.components.homekit.accessories import HomeBridge
from homeassistant.components.homekit.const import (
    CONF_AID, CONF_AUTO_START, CONF_EVENTS, HOMEKIT_NOTIFY_ID, QR_CODE_NAME)
from homeassistant.components.homekit.util import (
    validate_aid, validate_entities, validate_events_auto_start,
    show_setup_message, dismiss_setup_message, ATTR_CODE)
from homeassistant.components.persistent_notification import (
    SERVICE_CREATE, SERVICE_DISMISS, ATTR_NOTIFICATION_ID)
from homeassistant.const import (
    EVENT_CALL_SERVICE, ATTR_DOMAIN, ATTR_SERVICE, ATTR_SERVICE_DATA)

from tests.common import get_test_home_assistant


class TestUtil(unittest.TestCase):
    """Test all HomeKit util methods."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.events = []

        @callback
        def record_event(event):
            """Track called event."""
            self.events.append(event)

        self.hass.bus.listen(EVENT_CALL_SERVICE, record_event)

    def tearDown(self):
        """Stop down everything that was started."""
        self.hass.stop()

    def test_validate_aid(self):
        """Test validate aid."""
        for value, aids in {-1: None, 1: None, 2: [2]}.items():
            with self.assertRaises(vol.Invalid):
                validate_aid(None, value, aids)

        aids = set()
        self.assertEqual(validate_aid(None, 2, aids), 2)
        self.assertEqual(aids, {2})
        self.assertEqual(validate_aid(None, 3, aids), 3)
        self.assertEqual(aids, {2, 3})

    def test_validate_entities(self):
        """Test validate entities."""
        # General failures
        configs = [{'demo.test': 1}, {'demo.test': 2, 'light.demo': 2},
                   {'demo.test': '1'}, {'demo.test': [1]},
                   {'demo.test': {'aid': '2'}}]

        for conf in configs:
            with self.assertRaises(vol.Invalid):
                validate_entities(conf)

        # Device specific failures
        configs = []

        for conf in configs:
            with self.assertRaises(vol.Invalid):
                validate_entities(conf)

        # General validations
        self.assertEqual(validate_entities(
            {'demo.test': 2}), {'demo.test': {CONF_AID: 2}})
        self.assertEqual(validate_entities(
            {'demo.test': {CONF_AID: 2}}), {'demo.test': {CONF_AID: 2}})
        self.assertEqual(
            validate_entities({'demo.test': 2, 'demo.test_2': 3}),
            {'demo.test': {CONF_AID: 2}, 'demo.test_2': {CONF_AID: 3}})

        # Device specific validations
        self.assertEqual(
            validate_entities({'alarm_control_panel.demo': {CONF_AID: 2}}),
            {'alarm_control_panel.demo': {CONF_AID: 2, ATTR_CODE: None}})
        self.assertEqual(
            validate_entities(
                {'alarm_control_panel.demo': {
                    CONF_AID: 2, ATTR_CODE: '1234'}}),
            {'alarm_control_panel.demo': {CONF_AID: 2, ATTR_CODE: '1234'}})

    def test_validate_events_auto_start(self):
        """Test validate events auto start method."""
        schema = vol.Schema(validate_events_auto_start)

        for value in ({CONF_EVENTS: ['event'], CONF_AUTO_START: False}, ):
            with self.assertRaises(vol.Invalid):
                schema(value)

        for value in ({CONF_EVENTS: ['event'], CONF_AUTO_START: True},
                      {CONF_EVENTS: [], CONF_AUTO_START: True},
                      {CONF_EVENTS: [], CONF_AUTO_START: False}):
            schema(value)

    def test_show_setup_msg(self):
        """Test show setup message as persistence notification."""
        bridge = HomeBridge(self.hass)

        with patch('homeassistant.components.homekit.accessories.'
                   'HomeBridge.qr_code') as mock_qr_code, \
                patch('os.path.isfile') as mock_is_file:
            mock_is_file.side_effect = [True, False]
            mock_qr_code.png.side_effect = [None, OSError]
            show_setup_message(bridge, self.hass)
            self.hass.block_till_done()
            show_setup_message(bridge, self.hass)
            self.hass.block_till_done()

        path = self.hass.config.path('www/' + QR_CODE_NAME)
        self.assertEqual(
            mock_qr_code.mock_calls[0],
            call.png(path, background=ANY, quiet_zone=ANY, scale=ANY))

        data = self.events[0].data
        self.assertEqual(
            data.get(ATTR_DOMAIN, None), 'persistent_notification')
        self.assertEqual(data.get(ATTR_SERVICE, None), SERVICE_CREATE)
        self.assertNotEqual(data.get(ATTR_SERVICE_DATA, None), None)
        self.assertEqual(
            data[ATTR_SERVICE_DATA].get(ATTR_NOTIFICATION_ID, None),
            HOMEKIT_NOTIFY_ID)

    def test_dismiss_setup_msg(self):
        """Test dismiss setup message."""
        with patch('os.remove') as mock_remove:
            mock_remove.side_effect = [True, OSError]
            dismiss_setup_message(self.hass)
            self.hass.block_till_done()
            dismiss_setup_message(self.hass)
            self.hass.block_till_done()

        data = self.events[0].data
        self.assertEqual(
            data.get(ATTR_DOMAIN, None), 'persistent_notification')
        self.assertEqual(data.get(ATTR_SERVICE, None), SERVICE_DISMISS)
        self.assertNotEqual(data.get(ATTR_SERVICE_DATA, None), None)
        self.assertEqual(
            data[ATTR_SERVICE_DATA].get(ATTR_NOTIFICATION_ID, None),
            HOMEKIT_NOTIFY_ID)
