"""Define tests for the SimpliSafe config flow."""
from unittest.mock import patch

import pytest
from simplipy.api import AuthStates
from simplipy.errors import InvalidCredentialsError, SimplipyError, Verify2FAPending

from homeassistant import data_entry_flow
from homeassistant.components.simplisafe import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_CODE, CONF_TOKEN, CONF_USERNAME

from .common import REFRESH_TOKEN, USER_ID, USERNAME

CONF_USER_ID = "user_id"


async def test_duplicate_error(
    hass, config_entry, credentials_config, setup_simplisafe, sms_config
):
    """Test that errors are shown when duplicates are added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=credentials_config
    )
    assert result["step_id"] == "sms_2fa"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=sms_config
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass, config_entry):
    """Test config flow options."""
    with patch(
        "homeassistant.components.simplisafe.async_setup_entry", return_value=True
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_CODE: "4321"}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert config_entry.options == {CONF_CODE: "4321"}


@pytest.mark.parametrize("unique_id", [USERNAME, USER_ID])
async def test_step_reauth(
    hass, config, config_entry, reauth_config, setup_simplisafe, sms_config
):
    """Test the re-auth step (testing both username and user ID as unique ID)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_REAUTH}, data=config
    )
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=reauth_config
    )
    assert result["step_id"] == "sms_2fa"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=sms_config
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "reauth_successful"

    assert len(hass.config_entries.async_entries()) == 1
    [config_entry] = hass.config_entries.async_entries(DOMAIN)
    assert config_entry.unique_id == USER_ID
    assert config_entry.data == config


@pytest.mark.parametrize(
    "exc,error_string",
    [(InvalidCredentialsError, "invalid_auth"), (SimplipyError, "unknown")],
)
async def test_step_reauth_errors(hass, config, error_string, exc, reauth_config):
    """Test that errors during the reauth step are handled."""
    with patch(
        "homeassistant.components.simplisafe.API.async_from_credentials",
        side_effect=exc,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_REAUTH}, data=config
        )
        assert result["step_id"] == "reauth_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=reauth_config
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": error_string}


@pytest.mark.parametrize(
    "config,unique_id",
    [
        (
            {
                CONF_TOKEN: REFRESH_TOKEN,
                CONF_USER_ID: USER_ID,
            },
            USERNAME,
        ),
        (
            {
                CONF_TOKEN: REFRESH_TOKEN,
                CONF_USER_ID: USER_ID,
            },
            USER_ID,
        ),
    ],
)
async def test_step_reauth_from_scratch(
    hass, config, config_entry, credentials_config, setup_simplisafe, sms_config
):
    """Test the re-auth step when a complete redo is needed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_REAUTH}, data=config
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=credentials_config
    )
    assert result["step_id"] == "sms_2fa"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=sms_config
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "reauth_successful"

    assert len(hass.config_entries.async_entries()) == 1
    [config_entry] = hass.config_entries.async_entries(DOMAIN)
    assert config_entry.unique_id == USER_ID
    assert config_entry.data == {
        CONF_TOKEN: REFRESH_TOKEN,
        CONF_USERNAME: USERNAME,
    }


@pytest.mark.parametrize(
    "exc,error_string",
    [(InvalidCredentialsError, "invalid_auth"), (SimplipyError, "unknown")],
)
async def test_step_user_errors(hass, credentials_config, error_string, exc):
    """Test that errors during the user step are handled."""
    with patch(
        "homeassistant.components.simplisafe.API.async_from_credentials",
        side_effect=exc,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["step_id"] == "user"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=credentials_config
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": error_string}


@pytest.mark.parametrize("api_auth_state", [AuthStates.PENDING_2FA_EMAIL])
async def test_step_user_email_2fa(
    api, hass, config, credentials_config, setup_simplisafe
):
    """Test the user step with email-based 2FA."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    # Patch API.async_verify_2fa_email to first return pending, then return all done:
    api.async_verify_2fa_email.side_effect = [Verify2FAPending, None]

    # Patch the amount of time slept between calls so to not slow down this test:
    with patch(
        "homeassistant.components.simplisafe.config_flow.DEFAULT_EMAIL_2FA_SLEEP", 0
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=credentials_config
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

    assert len(hass.config_entries.async_entries()) == 1
    [config_entry] = hass.config_entries.async_entries(DOMAIN)
    assert config_entry.unique_id == USER_ID
    assert config_entry.data == config


@pytest.mark.parametrize("api_auth_state", [AuthStates.PENDING_2FA_EMAIL])
async def test_step_user_email_2fa_timeout(
    api, hass, config, credentials_config, setup_simplisafe
):
    """Test a timeout during the user step with email-based 2FA."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    # Patch API.async_verify_2fa_email to return pending:
    api.async_verify_2fa_email.side_effect = Verify2FAPending

    # Patch the amount of time slept between calls and the timeout duration so to not
    # slow down this test:
    with patch(
        "homeassistant.components.simplisafe.config_flow.DEFAULT_EMAIL_2FA_SLEEP", 0
    ), patch(
        "homeassistant.components.simplisafe.config_flow.DEFAULT_EMAIL_2FA_TIMEOUT", 0
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=credentials_config
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "2fa_timed_out"}


async def test_step_user_sms_2fa(
    hass, config, credentials_config, setup_simplisafe, sms_config
):
    """Test the user step with SMS-based 2FA."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=credentials_config
    )
    assert result["step_id"] == "sms_2fa"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=sms_config
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

    assert len(hass.config_entries.async_entries()) == 1
    [config_entry] = hass.config_entries.async_entries(DOMAIN)
    assert config_entry.unique_id == USER_ID
    assert config_entry.data == config


@pytest.mark.parametrize(
    "exc,error_string", [(InvalidCredentialsError, "invalid_auth")]
)
async def test_step_user_sms_2fa_errors(
    api,
    hass,
    config,
    credentials_config,
    error_string,
    exc,
    setup_simplisafe,
    sms_config,
):
    """Test that errors during the SMS-based 2FA step are handled."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=credentials_config
    )
    assert result["step_id"] == "sms_2fa"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    # Simulate entering the incorrect SMS code:
    api.async_verify_2fa_sms.side_effect = InvalidCredentialsError

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=sms_config
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"code": error_string}
