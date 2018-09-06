"""The tests for the Jewish calendar sensor platform."""
import unittest
from datetime import datetime as dt
from unittest.mock import patch

from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.setup import setup_component
from homeassistant.components.sensor.jewish_calendar import JewishCalSensor
from tests.common import get_test_home_assistant


class TestJewishCalenderSensor(unittest.TestCase):
    """Test the Jewish Calendar sensor."""

    def setUp(self):
        """Set up things to run when tests begin."""
        self.hass = get_test_home_assistant()

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    def checkForLoggingErrors(self):
        """Check whether logger spitted out errors."""
        errors = [rec for rec in self.cm.records if rec.levelname == "ERROR"]
        self.assertFalse(errors, ("Logger reported error(s): ",
                                  [err.getMessage() for err in errors]))

    def test_jewish_calendar_min_config(self):
        """Test minimum jewish calendar configuration."""
        config = {
            'sensor': {
                'platform': 'jewish_calendar'
            }
        }
        with self.assertLogs() as self.cm:
            assert setup_component(self.hass, 'sensor', config)
        self.checkForLoggingErrors()

    def test_jewish_calendar_hebrew(self):
        """Test jewish calendar sensor with language set to hebrew."""
        config = {
            'sensor': {
                'platform': 'jewish_calendar',
                'language': 'hebrew',
            }
        }
        with self.assertLogs() as self.cm:
            assert setup_component(self.hass, 'sensor', config)
        self.checkForLoggingErrors()

    def test_jewish_calendar_multiple_sensors(self):
        """Test jewish calendar sensor with multiple sensors setup."""
        config = {
            'sensor': {
                'platform': 'jewish_calendar',
                'sensors': [
                    'date', 'weekly_portion', 'holiday_name',
                    'holyness', 'first_light', 'gra_end_shma',
                    'mga_end_shma', 'plag_mincha', 'first_stars'
                ]
            }
        }
        with self.assertLogs() as self.cm:
            assert setup_component(self.hass, 'sensor', config)
        self.checkForLoggingErrors()

    def test_jewish_calendar_sensor_date_output(self):
        """Test Jewish calendar sensor date output."""
        test_time = dt(2018, 9, 3)
        sensor = JewishCalSensor(
            name='test', language='english', sensor_type='date')
        with patch('homeassistant.util.dt.now', return_value=test_time):
            run_coroutine_threadsafe(
                sensor.async_update(),
                self.hass.loop).result()
            self.assertEqual(sensor.state, '23 Elul 5778')

    def test_jewish_calendar_sensor_date_output_hebrew(self):
        """Test Jewish calendar sensor date output in hebrew."""
        test_time = dt(2018, 9, 3)
        sensor = JewishCalSensor(
            name='test', language='hebrew', sensor_type='date')
        with patch('homeassistant.util.dt.now', return_value=test_time):
            run_coroutine_threadsafe(
                sensor.async_update(),
                self.hass.loop).result()
            self.assertEqual(sensor.state, "כ\"ג באלול ה\' תשע\"ח")

    def test_jewish_calendar_sensor_holiday_name(self):
        """Test Jewish calendar sensor date output in hebrew."""
        test_time = dt(2018, 9, 10)
        sensor = JewishCalSensor(
            name='test', language='hebrew', sensor_type='holiday_name')
        with patch('homeassistant.util.dt.now', return_value=test_time):
            run_coroutine_threadsafe(
                sensor.async_update(),
                self.hass.loop).result()
            self.assertEqual(sensor.state, "א\' ראש השנה")

    def test_jewish_calendar_sensor_torah_reading(self):
        """Test Jewish calendar sensor date output in hebrew."""
        test_time = dt(2018, 9, 8)
        sensor = JewishCalSensor(
            name='test', language='hebrew', sensor_type='weekly_portion')
        with patch('homeassistant.util.dt.now', return_value=test_time):
            run_coroutine_threadsafe(
                sensor.async_update(),
                self.hass.loop).result()
            self.assertEqual(sensor.state, "נצבים")
