"""Tests for the iCloud config flow."""
import pytest
from unittest.mock import patch
from pyicloud.exceptions import PyiCloudFailedLoginException

from homeassistant import data_entry_flow
from homeassistant.components.icloud import config_flow
from homeassistant.components.icloud.config_flow import CONF_TRUSTED_DEVICE
from homeassistant.components.icloud.const import (
    DOMAIN,
    CONF_ACCOUNTNAME,
    CONF_GPS_ACCURACY_THRESHOLD,
    CONF_MAX_INTERVAL,
    DEFAULT_GPS_ACCURACY_THRESHOLD,
    DEFAULT_MAX_INTERVAL,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from tests.common import MockConfigEntry

USERNAME = "username@me.com"
PASSWORD = "password"
ACCOUNTNAME = "Account name 1 2 3"
ACCOUNTNAME_FROM_USERNAME = "username"
MAX_INTERVAL = 15
GPS_ACCURACY_THRESHOLD = 250


@pytest.fixture(name="requires_2fa")
def mock_controller_requires_2fa():
    """Mock a successful requires_2fa."""
    with patch("pyicloud.PyiCloudService.requires_2fa", return_value=True):
        yield


@pytest.fixture(name="send_verification_code")
def mock_controller_send_verification_code():
    """Mock a successful send_verification_code."""
    with patch("pyicloud.PyiCloudService.send_verification_code", return_value=True):
        yield


@pytest.fixture(name="validate_verification_code")
def mock_controller_validate_verification_code():
    """Mock a successful validate_verification_code."""
    with patch(
        "pyicloud.PyiCloudService.validate_verification_code", return_value=True
    ):
        yield


def init_config_flow(hass):
    """Init a configuration flow."""
    flow = config_flow.IcloudFlowHandler()
    flow.hass = hass
    return flow


async def test_user(
    hass, requires_2fa, send_verification_code, validate_verification_code
):
    """Test user config."""
    flow = init_config_flow(hass)

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # test with all provided
    result = await flow.async_step_user(
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_ACCOUNTNAME] == ACCOUNTNAME_FROM_USERNAME
    assert result["data"][CONF_MAX_INTERVAL] == DEFAULT_MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == DEFAULT_GPS_ACCURACY_THRESHOLD


async def test_import(
    hass, requires_2fa, send_verification_code, validate_verification_code
):
    """Test import step."""
    flow = init_config_flow(hass)

    # import with username and password
    result = await flow.async_step_import(
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_ACCOUNTNAME] == ACCOUNTNAME_FROM_USERNAME
    assert result["data"][CONF_MAX_INTERVAL] == DEFAULT_MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == DEFAULT_GPS_ACCURACY_THRESHOLD

    # import with all
    result = await flow.async_step_import(
        {
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_ACCOUNTNAME: ACCOUNTNAME,
            CONF_MAX_INTERVAL: MAX_INTERVAL,
            CONF_GPS_ACCURACY_THRESHOLD: GPS_ACCURACY_THRESHOLD,
        }
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_ACCOUNTNAME] == ACCOUNTNAME
    assert result["data"][CONF_MAX_INTERVAL] == MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == GPS_ACCURACY_THRESHOLD


async def test_abort_if_already_setup(
    hass, requires_2fa, send_verification_code, validate_verification_code
):
    """Test we abort if Linky is already setup."""
    flow = init_config_flow(hass)
    MockConfigEntry(
        domain=DOMAIN, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    ).add_to_hass(hass)

    # Should fail, same USERNAME (import)
    result = await flow.async_step_import(
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "username_exists"

    # Should fail, same ACCOUNTNAME (import)
    result = await flow.async_step_import(
        {
            CONF_USERNAME: "other_username@icloud.com",
            CONF_PASSWORD: PASSWORD,
            CONF_ACCOUNTNAME: USERNAME,
        }
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "username_exists"

    # Should fail, same USERNAME (flow)
    result = await flow.async_step_user(
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {CONF_USERNAME: "username_exists"}

    # Should fail, same ACCOUNTNAME (flow)
    result = await flow.async_step_user(
        {
            CONF_USERNAME: "other_username@icloud.com",
            CONF_PASSWORD: PASSWORD,
            CONF_ACCOUNTNAME: USERNAME,
        }
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["reason"] == {CONF_USERNAME: "username_exists"}


async def test_abort_on_login_failed(hass):
    """Test when we have errors during login."""
    flow = init_config_flow(hass)

    with patch(
        "pyicloud.PyiCloudService.authenticate",
        side_effect=PyiCloudFailedLoginException(),
    ):
        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "login"}


async def test_abort_on_fetch_failed(hass, requires_2fa):
    """Test when we have errors during fetch."""
    flow = init_config_flow(hass)

    with patch("pyicloud.PyiCloudService.send_verification_code", side_effect=False):
        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {CONF_TRUSTED_DEVICE: "send_verification_code"}

    with patch(
        "pyicloud.PyiCloudService.validate_verification_code", side_effect=False
    ):
        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "validate_verification_code"}
