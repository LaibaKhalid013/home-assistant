"""Test config flow."""

from unittest.mock import patch

from aiomusiccast import MusicCastConnectionException
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import ssdp
from homeassistant.components.yamaha_musiccast.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
async def silent_ssdp_scanner(hass):
    """Start SSDP component and get Scanner, prevent actual SSDP traffic."""
    with patch(
        "homeassistant.components.ssdp.Scanner._async_start_ssdp_listeners"
    ), patch("homeassistant.components.ssdp.Scanner._async_stop_ssdp_listeners"), patch(
        "homeassistant.components.ssdp.Scanner.async_scan"
    ):
        yield


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.yamaha_musiccast.async_setup_entry", return_value=True
    ):
        yield


@pytest.fixture
def mock_get_device_info_valid():
    """Mock getting valid device info from musiccast API."""
    with patch(
        "aiomusiccast.MusicCastDevice.get_device_info",
        return_value={"system_id": "1234567890", "model_name": "MC20"},
    ):
        yield


@pytest.fixture
def mock_get_device_info_invalid():
    """Mock getting invalid device info from musiccast API."""
    with patch(
        "aiomusiccast.MusicCastDevice.get_device_info",
        return_value={"type": "no_yamaha"},
    ):
        yield


@pytest.fixture
def mock_get_device_info_exception():
    """Mock raising an unexpected Exception."""
    with patch(
        "aiomusiccast.MusicCastDevice.get_device_info",
        side_effect=Exception("mocked error"),
    ):
        yield


@pytest.fixture
def mock_get_device_info_mc_exception():
    """Mock raising an unexpected Exception."""
    with patch(
        "aiomusiccast.MusicCastDevice.get_device_info",
        side_effect=MusicCastConnectionException("mocked error"),
    ):
        yield


@pytest.fixture
def mock_ssdp_yamaha():
    """Mock that the SSDP detected device is a musiccast device."""
    with patch("aiomusiccast.MusicCastDevice.check_yamaha_ssdp", return_value=True):
        yield


@pytest.fixture
def mock_ssdp_no_yamaha():
    """Mock that the SSDP detected device is not a musiccast device."""
    with patch("aiomusiccast.MusicCastDevice.check_yamaha_ssdp", return_value=False):
        yield


@pytest.fixture
def mock_valid_discovery_information():
    """Mock that the ssdp scanner returns a useful upnp description."""
    with patch(
        "homeassistant.components.ssdp.async_get_discovery_info_by_st",
        return_value=[
            ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://127.0.0.1:9000/MediaRenderer/desc.xml",
                ssdp_headers={
                    "_host": "127.0.0.1",
                },
                upnp={},
            )
        ],
    ):
        yield


@pytest.fixture
def mock_empty_discovery_information():
    """Mock that the ssdp scanner returns no upnp description."""
    with patch(
        "homeassistant.components.ssdp.async_get_discovery_info_by_st", return_value=[]
    ):
        yield


# User Flows


async def test_user_input_device_not_found(
    hass, mock_get_device_info_mc_exception, mock_get_source_ip
):
    """Test when user specifies a non-existing device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "none"},
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_input_non_yamaha_device_found(
    hass, mock_get_device_info_invalid, mock_get_source_ip
):
    """Test when user specifies an existing device, which does not provide the musiccast API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "127.0.0.1"},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "no_musiccast_device"}


async def test_user_input_device_already_existing(
    hass, mock_get_device_info_valid, mock_get_source_ip
):
    """Test when user specifies an existing device."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1234567890",
        data={CONF_HOST: "192.168.188.18", "model": "MC20", "serial": "1234567890"},
    )
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "192.168.188.18"},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result2["reason"] == "already_configured"


async def test_user_input_unknown_error(
    hass, mock_get_device_info_exception, mock_get_source_ip
):
    """Test when user specifies an existing device, which does not provide the musiccast API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "127.0.0.1"},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_user_input_device_found(
    hass,
    mock_get_device_info_valid,
    mock_valid_discovery_information,
    mock_get_source_ip,
):
    """Test when user specifies an existing device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "127.0.0.1"},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert isinstance(result2["result"], ConfigEntry)
    assert result2["data"] == {
        "host": "127.0.0.1",
        "serial": "1234567890",
        "upnp_description": "http://127.0.0.1:9000/MediaRenderer/desc.xml",
    }


async def test_user_input_device_found_no_ssdp(
    hass,
    mock_get_device_info_valid,
    mock_empty_discovery_information,
    mock_get_source_ip,
):
    """Test when user specifies an existing device, which no discovery data are present for."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "127.0.0.1"},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert isinstance(result2["result"], ConfigEntry)
    assert result2["data"] == {
        "host": "127.0.0.1",
        "serial": "1234567890",
        "upnp_description": "http://127.0.0.1:49154/MediaRenderer/desc.xml",
    }


async def test_import_device_already_existing(
    hass, mock_get_device_info_valid, mock_get_source_ip
):
    """Test when the configurations.yaml contains an existing device."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1234567890",
        data={CONF_HOST: "192.168.188.18", "model": "MC20", "serial": "1234567890"},
    )
    mock_entry.add_to_hass(hass)

    config = {"platform": "yamaha_musiccast", "host": "192.168.188.18", "port": 5006}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_import_error(hass, mock_get_device_info_exception, mock_get_source_ip):
    """Test when in the configuration.yaml a device is configured, which cannot be added.."""
    config = {"platform": "yamaha_musiccast", "host": "192.168.188.18", "port": 5006}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "unknown"}


async def test_import_device_successful(
    hass,
    mock_get_device_info_valid,
    mock_valid_discovery_information,
    mock_get_source_ip,
):
    """Test when the device was imported successfully."""
    config = {"platform": "yamaha_musiccast", "host": "127.0.0.1", "port": 5006}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert isinstance(result["result"], ConfigEntry)
    assert result["data"] == {
        "host": "127.0.0.1",
        "serial": "1234567890",
        "upnp_description": "http://127.0.0.1:9000/MediaRenderer/desc.xml",
    }


# SSDP Flows


async def test_ssdp_discovery_failed(hass, mock_ssdp_no_yamaha, mock_get_source_ip):
    """Test when an SSDP discovered device is not a musiccast device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=ssdp.SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location="http://127.0.0.1/desc.xml",
            upnp={
                ssdp.ATTR_UPNP_MODEL_NAME: "MC20",
                ssdp.ATTR_UPNP_SERIAL: "123456789",
            },
        ),
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "yxc_control_url_missing"


async def test_ssdp_discovery_successful_add_device(
    hass, mock_ssdp_yamaha, mock_get_source_ip
):
    """Test when the SSDP discovered device is a musiccast device and the user confirms it."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=ssdp.SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location="http://127.0.0.1/desc.xml",
            upnp={
                ssdp.ATTR_UPNP_MODEL_NAME: "MC20",
                ssdp.ATTR_UPNP_SERIAL: "1234567890",
            },
        ),
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] is None
    assert result["step_id"] == "confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert isinstance(result2["result"], ConfigEntry)
    assert result2["data"] == {
        "host": "127.0.0.1",
        "serial": "1234567890",
        "upnp_description": "http://127.0.0.1/desc.xml",
    }


async def test_ssdp_discovery_existing_device_update(
    hass, mock_ssdp_yamaha, mock_get_source_ip
):
    """Test when the SSDP discovered device is a musiccast device, but it already exists with another IP."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1234567890",
        data={CONF_HOST: "192.168.188.18", "model": "MC20", "serial": "1234567890"},
    )
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=ssdp.SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location="http://127.0.0.1/desc.xml",
            upnp={
                ssdp.ATTR_UPNP_MODEL_NAME: "MC20",
                ssdp.ATTR_UPNP_SERIAL: "1234567890",
            },
        ),
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"
    assert mock_entry.data[CONF_HOST] == "127.0.0.1"
    assert mock_entry.data["upnp_description"] == "http://127.0.0.1/desc.xml"
