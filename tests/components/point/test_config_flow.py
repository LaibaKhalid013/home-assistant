"""Tests for the Point config flow."""
import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import data_entry_flow
from homeassistant.components.point import DOMAIN, config_flow
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.typing import ClientSessionGenerator


def init_config_flow(hass, side_effect=None):
    """Init a configuration flow."""
    config_flow.register_flow_implementation(
        hass,
        DOMAIN,
        "id",
        "secret",
        "redirect_uri",
    )
    flow = config_flow.PointFlowHandler()
    flow._get_authorization_url = AsyncMock(
        return_value="https://example.com", side_effect=side_effect
    )
    flow.hass = hass
    return flow


@pytest.fixture
def is_authorized():
    """Set PointSession authorized."""
    return True


@pytest.fixture
def mock_pypoint(is_authorized):
    """Mock pypoint."""
    with patch(
        "homeassistant.components.point.config_flow.PointSession"
    ) as PointSession:
        PointSession.return_value.get_access_token = AsyncMock(
            return_value={"access_token": "boo"}
        )
        PointSession.return_value.is_authorized = is_authorized
        PointSession.return_value.user = AsyncMock(
            return_value={"email": "john.doe@example.com"}
        )
        yield PointSession


async def test_abort_if_no_implementation_registered(hass: HomeAssistant) -> None:
    """Test we abort if no implementation is registered."""
    flow = config_flow.PointFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "no_flows"


async def test_abort_if_already_setup(hass: HomeAssistant) -> None:
    """Test we abort if Point is already setup."""
    flow = init_config_flow(hass)

    with patch.object(hass.config_entries, "async_entries", return_value=[{}]):
        result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_setup"

    with patch.object(hass.config_entries, "async_entries", return_value=[{}]):
        result = await flow.async_step_import()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_setup"


async def test_full_flow_implementation(hass: HomeAssistant, mock_pypoint) -> None:
    """Test registering an implementation and finishing flow works."""
    config_flow.register_flow_implementation(
        hass,
        "test-other",
        "id",
        "secret",
        "refresh_uri",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"code"}
    )
    assert result["type"] == FlowResultType.EXTERNAL_STEP_DONE

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["token"] == {"access_token": "boo"}
    assert result["data"]["refresh_args"] == {
        CONF_CLIENT_ID: "id",
        CONF_CLIENT_SECRET: "secret",
    }
    assert result["title"] == "john.doe@example.com"


async def test_step_import(hass: HomeAssistant, mock_pypoint) -> None:
    """Test that we trigger import when configuring with client."""
    flow = init_config_flow(hass)

    result = await flow.async_step_import()
    assert result["type"] == data_entry_flow.FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "auth"


async def test_abort_if_timeout_generating_auth_url(hass: HomeAssistant) -> None:
    """Test we abort if generating authorize url fails."""
    flow = init_config_flow(hass, side_effect=asyncio.TimeoutError)

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "authorize_url_timeout"


async def test_abort_if_exception_generating_auth_url(hass: HomeAssistant) -> None:
    """Test we abort if generating authorize url blows up."""
    flow = init_config_flow(hass, side_effect=ValueError)

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "unknown_authorize_url_generation"


async def test_callback_view(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_pypoint,
) -> None:
    """Test callback view."""
    config_flow.register_flow_implementation(
        hass, "test-other", "id", "secret", "refresh_uri"
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "auth"

    client = await hass_client_no_auth()
    forward_url = config_flow.AUTH_CALLBACK_PATH

    resp = await client.get(forward_url)
    assert resp.status == HTTPStatus.OK
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.EXTERNAL_STEP_DONE
    assert result["step_id"] == "finish"
