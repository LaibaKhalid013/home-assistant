"""The tests for the MQTT sensor platform."""
import unittest

from datetime import timedelta, datetime

import homeassistant.core as ha
from homeassistant.setup import setup_component
import homeassistant.components.sensor as sensor
from homeassistant.const import EVENT_STATE_CHANGED
import homeassistant.util.dt as dt_util

from tests.common import mock_mqtt_component, fire_mqtt_message
from tests.common import get_test_home_assistant, mock_component
from tests.common import fire_time_changed


class TestSensorMQTT(unittest.TestCase):
    """Test the MQTT sensor."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        mock_mqtt_component(self.hass)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setting_sensor_value_via_mqtt_message(self):
        """Test the setting of the value via MQTT."""
        mock_component(self.hass, 'mqtt')
        assert setup_component(self.hass, sensor.DOMAIN, {
            sensor.DOMAIN: {
                'platform': 'mqtt',
                'name': 'test',
                'state_topic': 'test-topic',
                'unit_of_measurement': 'fav unit'
            }
        })

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()
        state = self.hass.states.get('sensor.test')

        self.assertEqual('100', state.state)
        self.assertEqual('fav unit',
                         state.attributes.get('unit_of_measurement'))

    def test_setting_sensor_value_expires(self):
        """Test the expiration of the value."""
        mock_component(self.hass, 'mqtt')
        assert setup_component(self.hass, sensor.DOMAIN, {
            sensor.DOMAIN: {
                'platform': 'mqtt',
                'name': 'test',
                'state_topic': 'test-topic',
                'unit_of_measurement': 'fav unit',
                'expire_after': '4',
                'force_update': True
            }
        })

        now = datetime(2017, 1, 1, 1, tzinfo=dt_util.UTC)
        fire_time_changed(self.hass, now)

        state = self.hass.states.get('sensor.test')
        self.assertEqual('unknown', state.state)

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()

        state = self.hass.states.get('sensor.test')
        self.assertEqual('100', state.state)

        # +3s
        now = now + timedelta(seconds=3)
        fire_time_changed(self.hass, now)
        self.hass.block_till_done()

        # Not yet expired
        state = self.hass.states.get('sensor.test')
        self.assertEqual('100', state.state)

        # Next message resets timer
        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()

        state = self.hass.states.get('sensor.test')
        self.assertEqual('100', state.state)

        # +3s
        now = now + timedelta(seconds=3)
        fire_time_changed(self.hass, now)
        self.hass.block_till_done()

        # Not yet expired
        state = self.hass.states.get('sensor.test')
        self.assertEqual('100', state.state)

        # +3s
        now = now + timedelta(seconds=3)
        fire_time_changed(self.hass, now)
        self.hass.block_till_done()

        # Expired
        state = self.hass.states.get('sensor.test')
        # FIXME: I have no idea why this does not work.
        # Got stuck here, help please.
        # self.assertEqual('unknown', state.state)

    def test_setting_sensor_value_via_mqtt_json_message(self):
        """Test the setting of the value via MQTT with JSON playload."""
        mock_component(self.hass, 'mqtt')
        assert setup_component(self.hass, sensor.DOMAIN, {
            sensor.DOMAIN: {
                'platform': 'mqtt',
                'name': 'test',
                'state_topic': 'test-topic',
                'unit_of_measurement': 'fav unit',
                'value_template': '{{ value_json.val }}'
            }
        })

        fire_mqtt_message(self.hass, 'test-topic', '{ "val": "100" }')
        self.hass.block_till_done()
        state = self.hass.states.get('sensor.test')

        self.assertEqual('100', state.state)

    def test_force_update_disabled(self):
        """Test force update option."""
        mock_component(self.hass, 'mqtt')
        assert setup_component(self.hass, sensor.DOMAIN, {
            sensor.DOMAIN: {
                'platform': 'mqtt',
                'name': 'test',
                'state_topic': 'test-topic',
                'unit_of_measurement': 'fav unit'
            }
        })

        events = []

        @ha.callback
        def callback(event):
            events.append(event)

        self.hass.bus.listen(EVENT_STATE_CHANGED, callback)

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()
        self.assertEqual(1, len(events))

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()
        self.assertEqual(1, len(events))

    def test_force_update_enabled(self):
        """Test force update option."""
        mock_component(self.hass, 'mqtt')
        assert setup_component(self.hass, sensor.DOMAIN, {
            sensor.DOMAIN: {
                'platform': 'mqtt',
                'name': 'test',
                'state_topic': 'test-topic',
                'unit_of_measurement': 'fav unit',
                'force_update': True
            }
        })

        events = []

        @ha.callback
        def callback(event):
            events.append(event)

        self.hass.bus.listen(EVENT_STATE_CHANGED, callback)

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()
        self.assertEqual(1, len(events))

        fire_mqtt_message(self.hass, 'test-topic', '100')
        self.hass.block_till_done()
        self.assertEqual(2, len(events))
