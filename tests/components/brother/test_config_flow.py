"""Define tests for the Brother Printer config flow."""
import json

from asynctest import patch
from brother import SnmpError, UnsupportedModel

from homeassistant import data_entry_flow
from homeassistant.components.brother import config_flow
from homeassistant.components.brother.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_TYPE

from tests.common import MockConfigEntry, load_fixture

CONFIG = {CONF_HOST: "localhost", CONF_TYPE: "laser"}


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER


async def test_create_entry_with_hostname(hass):
    """Test that the user step works with printer hostname."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == CONFIG[CONF_HOST]
        assert result["data"][CONF_TYPE] == CONFIG[CONF_TYPE]


async def test_create_entry_with_ip_address(hass):
    """Test that the user step works with printer IP address."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_HOST: "127.0.0.1", CONF_TYPE: "laser"},
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "127.0.0.1"
        assert result["data"][CONF_TYPE] == "laser"


async def test_invalid_hostname(hass):
    """Test invalid hostname in user_input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: "invalid/hostname", CONF_TYPE: "laser"},
    )

    assert result["errors"] == {CONF_HOST: "wrong_host"}


async def test_connection_error(hass):
    """Test connection to host error."""
    with patch("brother.Brother._get_data", side_effect=ConnectionError()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {"base": "connection_error"}


async def test_snmp_error(hass):
    """Test SNMP error."""
    with patch("brother.Brother._get_data", side_effect=SnmpError("error")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {"base": "snmp_error"}


async def test_unsupported_model_error(hass):
    """Test unsupported printer model error."""
    with patch("brother.Brother._get_data", side_effect=UnsupportedModel("error")):

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "unsupported_model"


async def test_device_exists_abort(hass):
    """Test we abort config flow if Brother printer already configured."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):
        MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG).add_to_hass(
            hass
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"


async def test_show_zeroconf_form(hass):
    """Test that the zeroconf form is served."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"hostname": "example.local.", "name": "Brother Printer"},
        )

        assert result["description_placeholders"]["model"] == "HL-L2340DW"
        assert result["description_placeholders"]["serial_number"] == "0123456789"
        assert result["step_id"] == "zeroconf_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM


async def test_zeroconf_no_data(hass):
    """Test we abort if zeroconf provides no data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "connection_error"


async def test_zeroconf_not_brother_printer_error(hass):
    """Test we abort zeroconf flow if printer isn't Brother."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"hostname": "example.local.", "name": "Another Printer"},
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "not_brother_printer"


async def test_zeroconf_no_device_name(hass):
    """Test we abort zeroconf flow if printer name is None."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"hostname": "example.local.", "name": None},
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "not_brother_printer"


async def test_zeroconf_snmp_error(hass):
    """Test we abort zeroconf flow on SNMP error."""
    with patch("brother.Brother._get_data", side_effect=SnmpError("error")):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"hostname": "example.local.", "name": "Brother Printer"},
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "connection_error"


async def test_zeroconf_device_exists_abort(hass):
    """Test we abort zeroconf flow if Brother printer already configured."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):
        MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG).add_to_hass(
            hass
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"hostname": "example.local.", "name": "Brother Printer"},
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"


async def test_zeroconf_confirm_create_entry(hass):
    """Test zeroconf confirmation and create config entry."""
    with patch(
        "brother.Brother._get_data",
        return_value=json.loads(load_fixture("brother_printer_data.json")),
    ):
        flow = config_flow.BrotherConfigFlow()
        flow.hass = hass
        flow.context = {"source": SOURCE_ZEROCONF}

        result = await flow.async_step_zeroconf(
            {"hostname": "example.local.", "name": "Brother Printer"}
        )

        assert flow.context["title_placeholders"]["model"] == "HL-L2340DW"
        assert flow.context["title_placeholders"]["serial_number"] == "0123456789"
        assert result["step_id"] == "zeroconf_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await flow.async_step_zeroconf_confirm(user_input={CONF_TYPE: "laser"})

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "example.local"
        assert result["data"][CONF_TYPE] == "laser"
