"""Define fixtures available for all tests."""
from unittest.mock import MagicMock, patch

from pyezviz import EzvizClient
from pyezviz.test_cam_rtsp import TestRTSPAuth
from pytest import fixture


@fixture(autouse=True)
def mock_ffmpeg(hass):
    """Mock ffmpeg is loaded."""
    hass.config.components.add("ffmpeg")


@fixture
def ezviz(hass):
    """Mock the EzvizApi for easier testing."""
    with patch.object(EzvizClient, "login", return_value=True), patch(
        "homeassistant.components.ezviz"
    ) as mock_ezviz:
        instance = mock_ezviz.return_value = EzvizClient(
            "test-username",
            "test-password",
            "test-region",
            "test-timeout",
        )

        instance.login = MagicMock(return_value=True)

        yield mock_ezviz


@fixture
def ezviz_load_cameras(hass):
    """Mock the EzvizApi for easier testing."""
    with patch.object(EzvizClient, "load_cameras", return_value=True), patch(
        "homeassistant.components.ezviz"
    ) as mock_ezviz_load_cameras:
        instance = mock_ezviz_load_cameras.return_value = EzvizClient(
            "test-username",
            "test-password",
            "test-region",
            "test-timeout",
        )

        instance.load_cameras = MagicMock(return_value=True)

        yield mock_ezviz_load_cameras


@fixture
def ezviz_get_detection_sensibility(hass):
    """Mock the EzvizApi for easier testing."""
    with patch.object(
        EzvizClient, "get_detection_sensibility", return_value=True
    ), patch(
        "homeassistant.components.ezviz.config_flow"
    ) as mock_ezviz_get_detection_sensibility:
        instance = mock_ezviz_get_detection_sensibility.return_value = EzvizClient(
            "test-username",
            "test-password",
            "test-region",
            "test-timeout",
        )

        instance.get_detection_sensibility = MagicMock(return_value=True)

        yield mock_ezviz_get_detection_sensibility


@fixture
def ezviz_test_rtsp(hass):
    """Mock the EzvizApi for easier testing."""
    with patch.object(TestRTSPAuth, "main", return_value=True), patch(
        "homeassistant.components.ezviz"
    ) as mock_ezviz_test_rtsp:
        instance = mock_ezviz_test_rtsp.return_value = TestRTSPAuth(
            "test-ip",
            "test-username",
            "test-password",
        )

        instance.main = MagicMock(return_value=True)

        yield mock_ezviz_test_rtsp


@fixture
def ezviz_test_rtsp_config_flow(hass):
    """Mock the EzvizApi for easier testing."""
    with patch.object(TestRTSPAuth, "main", return_value=True), patch(
        "homeassistant.components.ezviz.config_flow.TestRTSPAuth"
    ) as mock_ezviz_test_rtsp:
        instance = mock_ezviz_test_rtsp.return_value = TestRTSPAuth(
            "test-ip",
            "test-username",
            "test-password",
        )

        instance.main = MagicMock(return_value=True)

        yield mock_ezviz_test_rtsp


@fixture
def ezviz_config_flow(hass):
    """Mock the EzvizAPI for easier config flow testing."""
    with patch.object(EzvizClient, "login", return_value=True), patch(
        "homeassistant.components.ezviz.config_flow.EzvizClient"
    ) as mock_ezviz:
        instance = mock_ezviz.return_value = EzvizClient(
            "test-username",
            "test-password",
            "test-region",
            "test-timeout",
        )

        instance.login = MagicMock(return_value=True)

        yield mock_ezviz
