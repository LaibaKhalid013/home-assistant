"""Test config flow."""
from homeassistant import config_entries

from tests.common import MockConfigEntry


async def test_mqtt_abort_if_existing_entry(hass, mqtt_mock):
    """Check MQTT flow aborts when an entry already exist."""
    MockConfigEntry(domain="tasmota").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        "tasmota", context={"source": config_entries.SOURCE_MQTT}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_mqtt_abort_invalid_topic(hass, mqtt_mock):
    """Check MQTT flow aborts if discovery topic is invalid."""
    discovery_info = {
        "topic": "",
        "payload": "",
        "qos": 0,
        "retain": False,
        "subscribed_topic": "custom_prefix/##",
        "timestamp": None,
    }
    result = await hass.config_entries.flow.async_init(
        "tasmota", context={"source": config_entries.SOURCE_MQTT}, data=discovery_info
    )
    assert result["type"] == "abort"
    assert result["reason"] == "invalid_discovery_info"


async def test_mqtt_setup(hass, mqtt_mock) -> None:
    """Test we can finish a config flow through MQTT with custom prefix."""
    discovery_info = {
        "topic": "",
        "payload": "",
        "qos": 0,
        "retain": False,
        "subscribed_topic": "custom_prefix/123/#",
        "timestamp": None,
    }
    result = await hass.config_entries.flow.async_init(
        "tasmota", context={"source": config_entries.SOURCE_MQTT}, data=discovery_info
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == "create_entry"
    assert result["result"].data == {
        "discovery_prefix": "custom_prefix/123",
    }


async def test_user_setup(hass, mqtt_mock):
    """Test we can finish a config flow."""
    result = await hass.config_entries.flow.async_init(
        "tasmota", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == "create_entry"
    assert result["result"].data == {
        "discovery_prefix": "tasmota/discovery",
    }


async def test_user_setup_advanced(hass, mqtt_mock):
    """Test we can finish a config flow."""
    result = await hass.config_entries.flow.async_init(
        "tasmota",
        context={"source": config_entries.SOURCE_USER, "show_advanced_options": True},
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"discovery_prefix": "test_tasmota/discovery"}
    )

    assert result["type"] == "create_entry"
    assert result["result"].data == {
        "discovery_prefix": "test_tasmota/discovery",
    }


async def test_user_setup_advanced_strip_wildcard(hass, mqtt_mock):
    """Test we can finish a config flow."""
    result = await hass.config_entries.flow.async_init(
        "tasmota",
        context={"source": config_entries.SOURCE_USER, "show_advanced_options": True},
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"discovery_prefix": "test_tasmota/discovery/#"}
    )

    assert result["type"] == "create_entry"
    assert result["result"].data == {
        "discovery_prefix": "test_tasmota/discovery",
    }


async def test_user_setup_invalid_topic_prefix(hass, mqtt_mock):
    """Test abort on invalid discovery topic."""
    result = await hass.config_entries.flow.async_init(
        "tasmota",
        context={"source": config_entries.SOURCE_USER, "show_advanced_options": True},
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"discovery_prefix": "tasmota/config/##"}
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_discovery_topic"


async def test_user_single_instance(hass, mqtt_mock):
    """Test we only allow a single config flow."""
    MockConfigEntry(domain="tasmota").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        "tasmota", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"
