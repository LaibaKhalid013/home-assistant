"""The tests for the TTS component."""
import os
import shutil
from unittest.mock import patch

import requests

import homeassistant.components.tts as tts
from homeassistant.components.tts.demo import DemoProvider
from homeassistant.components.media_player import (
    SERVICE_PLAY_MEDIA, MEDIA_TYPE_MUSIC, ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE, DOMAIN as DOMAIN_MP)
from homeassistant.bootstrap import setup_component

from tests.common import (
    get_test_home_assistant, assert_setup_component, mock_service)


class TestTTS(object):
    """Test the Google speech component."""

    def setup_method(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.demo_provider = DemoProvider()
        self.default_tts_cache = self.hass.config.path(tts.DEFAULT_CACHE_DIR)

    def teardown_method(self):
        """Stop everything that was started."""
        if os.path.isdir(self.default_tts_cache):
            shutil.rmtree(self.default_tts_cache)

        self.hass.stop()

    def test_setup_component_demo(self):
        """Setup the demo platform with defaults."""
        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        assert self.hass.services.has_service(tts.DOMAIN, 'demo_say')

    @patch('os.mkdir', side_effect=OSError(2, "No access"))
    def test_setup_component_demo_no_access_cache_folder(self, mock_mkdir):
        """Setup the demo platform with defaults."""
        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(0, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        assert not self.hass.services.has_service(tts.DOMAIN, 'demo_say')

    def test_setup_component_and_test_service(self):
        """Setup the demo platform and call service."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.services.call(tts.DOMAIN, 'demo_say', {
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        })
        self.hass.block_till_done()

        assert len(calls) == 1
        assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MEDIA_TYPE_MUSIC
        assert calls[0].data[ATTR_MEDIA_CONTENT_ID].find(
            "/api/tts_proxy/265944c108cbb00b2a621be5930513e03a0bb2cd"
            "_demo.mp3") \
            != -1
        assert os.path.isfile(os.path.join(
            self.default_tts_cache,
            "265944c108cbb00b2a621be5930513e03a0bb2cd_demo.mp3"))

    def test_setup_component_and_test_service_with_receive_voice(self):
        """Setup the demo platform and call service and receive voice."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.start()

        self.hass.services.call(tts.DOMAIN, 'demo_say', {
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        })
        self.hass.block_till_done()

        assert len(calls) == 1
        req = requests.get(calls[0].data[ATTR_MEDIA_CONTENT_ID])
        _, demo_data = self.demo_provider.get_tts_audio("bla")
        assert req.status_code == 200
        assert req.content == demo_data

    def test_setup_component_and_web_view_wrong_file(self):
        """Setup the demo platform and receive wrong file from web."""
        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.start()

        url = ("{}/api/tts_proxy/265944c108cbb00b2a621be5930513e03a0bb2cd"
               "_demo.mp3").format(self.hass.config.api.base_url)

        req = requests.get(url)
        assert req.status_code == 404

    def test_setup_component_and_web_view_wrong_filename(self):
        """Setup the demo platform and receive wrong filename from web."""
        config = {
            tts.DOMAIN: {
                'platform': 'demo',
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.start()

        url = ("{}/api/tts_proxy/265944dsk32c1b2a621be5930510bb2cd"
               "_demo.mp3").format(self.hass.config.api.base_url)

        req = requests.get(url)
        assert req.status_code == 404

    def test_setup_component_test_without_cache(self):
        """Setup demo platform without cache."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
                'cache': False,
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.services.call(tts.DOMAIN, 'demo_say', {
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        })
        self.hass.block_till_done()

        assert len(calls) == 1
        assert not os.path.isfile(os.path.join(
            self.default_tts_cache,
            "265944c108cbb00b2a621be5930513e03a0bb2cd_demo.mp3"))

    def test_setup_component_test_with_cache_call_service_without_cache(self):
        """Setup demo platform with cache and call service without cache."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
                'cache': True,
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.services.call(tts.DOMAIN, 'demo_say', {
            tts.ATTR_MESSAGE: "I person is on front of your door.",
            tts.ATTR_CACHE: False,
        })
        self.hass.block_till_done()

        assert len(calls) == 1
        assert not os.path.isfile(os.path.join(
            self.default_tts_cache,
            "265944c108cbb00b2a621be5930513e03a0bb2cd_demo.mp3"))

    def test_setup_component_test_with_cache_dir(self):
        """Setup demo platform with cache and call service without cache."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        _, demo_data = self.demo_provider.get_tts_audio("bla")
        cache_file = os.path.join(
            self.default_tts_cache,
            "265944c108cbb00b2a621be5930513e03a0bb2cd_demo.mp3")

        os.mkdir(self.default_tts_cache)
        with open(cache_file, "wb") as voice_file:
            voice_file.write(demo_data)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
                'cache': True,
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        with patch('homeassistant.components.tts.demo.DemoProvider.'
                   'get_tts_audio', return_value=None):
            self.hass.services.call(tts.DOMAIN, 'demo_say', {
                tts.ATTR_MESSAGE: "I person is on front of your door.",
            })
        self.hass.block_till_done()

        assert len(calls) == 1
        assert calls[0].data[ATTR_MEDIA_CONTENT_ID].find(
            "/api/tts_proxy/265944c108cbb00b2a621be5930513e03a0bb2cd"
            "_demo.mp3") \
            != -1

    @patch('homeassistant.components.tts.demo.DemoProvider.get_tts_audio',
           return_value=None)
    def test_setup_component_test_with_error_on_get_tts(self, tts_mock):
        """Setup demo platform with wrong get_tts_audio."""
        calls = mock_service(self.hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

        config = {
            tts.DOMAIN: {
                'platform': 'demo'
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.services.call(tts.DOMAIN, 'demo_say', {
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        })
        self.hass.block_till_done()

        assert len(calls) == 0

    def test_setup_component_load_cache_retrieve_without_mem_cache(self):
        """Setup component and load cache and get without mem cache."""
        _, demo_data = self.demo_provider.get_tts_audio("bla")
        cache_file = os.path.join(
            self.default_tts_cache,
            "265944c108cbb00b2a621be5930513e03a0bb2cd_demo.mp3")

        os.mkdir(self.default_tts_cache)
        with open(cache_file, "wb") as voice_file:
            voice_file.write(demo_data)

        config = {
            tts.DOMAIN: {
                'platform': 'demo',
                'cache': True,
            }
        }

        with assert_setup_component(1, tts.DOMAIN):
            setup_component(self.hass, tts.DOMAIN, config)

        self.hass.start()

        url = ("{}/api/tts_proxy/265944c108cbb00b2a621be5930513e03a0bb2cd"
               "_demo.mp3").format(self.hass.config.api.base_url)

        req = requests.get(url)
        assert req.status_code == 200
        assert req.content == demo_data
