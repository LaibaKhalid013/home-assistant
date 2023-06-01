"""The tests for the nexbus sensor component."""
from collections.abc import Generator
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components import sensor
from homeassistant.components.nextbus.const import (
    CONF_AGENCY,
    CONF_ROUTE,
    CONF_STOP,
    DOMAIN,
)
from homeassistant.components.nextbus.util import UserConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

VALID_AGENCY = "sf-muni"
VALID_ROUTE = "F"
VALID_STOP = "5650"
VALID_AGENCY_TITLE = "San Francisco Muni"
VALID_ROUTE_TITLE = "F-Market & Wharves"
VALID_STOP_TITLE = "Market St & 7th St"
SENSOR_ID_SHORT = "sensor.sf_muni_f"

PLATFORM_CONFIG = {
    sensor.DOMAIN: {
        "platform": DOMAIN,
        CONF_AGENCY: VALID_AGENCY,
        CONF_ROUTE: VALID_ROUTE,
        CONF_STOP: VALID_STOP,
    },
}


CONFIG_BASIC = {
    DOMAIN: {
        CONF_AGENCY: VALID_AGENCY,
        CONF_ROUTE: VALID_ROUTE,
        CONF_STOP: VALID_STOP,
    }
}

BASIC_RESULTS = {
    "predictions": {
        "agencyTitle": VALID_AGENCY_TITLE,
        "agencyTag": VALID_AGENCY,
        "routeTitle": VALID_ROUTE_TITLE,
        "routeTag": VALID_ROUTE,
        "stopTitle": VALID_STOP_TITLE,
        "stopTag": VALID_STOP,
        "direction": {
            "title": "Outbound",
            "prediction": [
                {"minutes": "1", "epochTime": "1553807371000"},
                {"minutes": "2", "epochTime": "1553807372000"},
                {"minutes": "3", "epochTime": "1553807373000"},
                {"minutes": "10", "epochTime": "1553807380000"},
            ],
        },
    }
}


@pytest.fixture
def mock_nextbus() -> Generator[MagicMock, None, None]:
    """Create a mock py_nextbus module."""
    with patch(
        "homeassistant.components.nextbus.sensor.NextBusClient",
    ) as NextBusClient:
        yield NextBusClient


@pytest.fixture
def mock_nextbus_predictions(
    mock_nextbus: MagicMock,
) -> Generator[MagicMock, None, None]:
    """Create a mock of NextBusClient predictions."""
    instance = mock_nextbus.return_value
    instance.get_predictions_for_multi_stops.return_value = BASIC_RESULTS

    return instance.get_predictions_for_multi_stops


@pytest.fixture
def mock_nextbus_lists(mock_nextbus: MagicMock) -> MagicMock:
    """Mock all list functions in nextbus to test validate logic."""
    instance = mock_nextbus.return_value
    instance.get_agency_list.return_value = {
        "agency": [{"tag": "sf-muni", "title": "San Francisco Muni"}]
    }
    instance.get_route_list.return_value = {
        "route": [{"tag": "F", "title": "F - Market & Wharves"}]
    }
    instance.get_route_config.return_value = {
        "route": {"stop": [{"tag": "5650", "title": "Market St & 7th St"}]}
    }

    return instance


async def assert_setup_sensor(
    hass: HomeAssistant,
    config: UserConfig,
    expected_state=ConfigEntryState.LOADED,
) -> MockConfigEntry:
    """Set up the sensor and assert it's been created."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=config[DOMAIN])
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is expected_state

    return config_entry


async def test_legacy_yaml_setup(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test config setup and yaml deprecation."""
    with patch(
        "homeassistant.components.nextbus.config_flow.NextBusClient",
    ) as NextBusClient:
        NextBusClient.return_value.get_predictions_for_multi_stops.return_value = (
            BASIC_RESULTS
        )
        await async_setup_component(hass, sensor.DOMAIN, PLATFORM_CONFIG)
        await hass.async_block_till_done()

    issue = issue_registry.async_get_issue(DOMAIN, "deprecated_yaml")
    assert issue


async def test_valid_config(
    hass: HomeAssistant, mock_nextbus: MagicMock, mock_nextbus_lists: MagicMock
) -> None:
    """Test that sensor is set up properly with valid config."""
    await assert_setup_sensor(hass, CONFIG_BASIC)


async def test_verify_valid_state(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify all attributes are set from a valid response."""
    await assert_setup_sensor(hass, CONFIG_BASIC)

    mock_nextbus_predictions.assert_called_once_with(
        [{"stop_tag": VALID_STOP, "route_tag": VALID_ROUTE}], VALID_AGENCY
    )

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.state == "2019-03-28T21:09:31+00:00"
    assert state.attributes["agency"] == VALID_AGENCY_TITLE
    assert state.attributes["route"] == VALID_ROUTE_TITLE
    assert state.attributes["stop"] == VALID_STOP_TITLE
    assert state.attributes["direction"] == "Outbound"
    assert state.attributes["upcoming"] == "1, 2, 3, 10"


async def test_message_dict(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify that a single dict message is rendered correctly."""
    mock_nextbus_predictions.return_value = {
        "predictions": {
            "agencyTitle": VALID_AGENCY_TITLE,
            "agencyTag": VALID_AGENCY,
            "routeTitle": VALID_ROUTE_TITLE,
            "routeTag": VALID_ROUTE,
            "stopTitle": VALID_STOP_TITLE,
            "stopTag": VALID_STOP,
            "message": {"text": "Message"},
            "direction": {
                "title": "Outbound",
                "prediction": [
                    {"minutes": "1", "epochTime": "1553807371000"},
                    {"minutes": "2", "epochTime": "1553807372000"},
                    {"minutes": "3", "epochTime": "1553807373000"},
                ],
            },
        }
    }

    await assert_setup_sensor(hass, CONFIG_BASIC)

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.attributes["message"] == "Message"


async def test_message_list(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify that a list of messages are rendered correctly."""
    mock_nextbus_predictions.return_value = {
        "predictions": {
            "agencyTitle": VALID_AGENCY_TITLE,
            "agencyTag": VALID_AGENCY,
            "routeTitle": VALID_ROUTE_TITLE,
            "routeTag": VALID_ROUTE,
            "stopTitle": VALID_STOP_TITLE,
            "stopTag": VALID_STOP,
            "message": [{"text": "Message 1"}, {"text": "Message 2"}],
            "direction": {
                "title": "Outbound",
                "prediction": [
                    {"minutes": "1", "epochTime": "1553807371000"},
                    {"minutes": "2", "epochTime": "1553807372000"},
                    {"minutes": "3", "epochTime": "1553807373000"},
                ],
            },
        }
    }

    await assert_setup_sensor(hass, CONFIG_BASIC)

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.attributes["message"] == "Message 1 -- Message 2"


async def test_direction_list(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify that a list of messages are rendered correctly."""
    mock_nextbus_predictions.return_value = {
        "predictions": {
            "agencyTitle": VALID_AGENCY_TITLE,
            "agencyTag": VALID_AGENCY,
            "routeTitle": VALID_ROUTE_TITLE,
            "routeTag": VALID_ROUTE,
            "stopTitle": VALID_STOP_TITLE,
            "stopTag": VALID_STOP,
            "message": [{"text": "Message 1"}, {"text": "Message 2"}],
            "direction": [
                {
                    "title": "Outbound",
                    "prediction": [
                        {"minutes": "1", "epochTime": "1553807371000"},
                        {"minutes": "2", "epochTime": "1553807372000"},
                        {"minutes": "3", "epochTime": "1553807373000"},
                    ],
                },
                {
                    "title": "Outbound 2",
                    "prediction": {"minutes": "0", "epochTime": "1553807374000"},
                },
            ],
        }
    }

    await assert_setup_sensor(hass, CONFIG_BASIC)

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.state == "2019-03-28T21:09:31+00:00"
    assert state.attributes["agency"] == VALID_AGENCY_TITLE
    assert state.attributes["route"] == VALID_ROUTE_TITLE
    assert state.attributes["stop"] == VALID_STOP_TITLE
    assert state.attributes["direction"] == "Outbound, Outbound 2"
    assert state.attributes["upcoming"] == "0, 1, 2, 3"


async def test_custom_name(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify that a custom name can be set via config."""
    config = deepcopy(CONFIG_BASIC)
    config[DOMAIN][CONF_NAME] = "Custom Name"

    await assert_setup_sensor(hass, config)
    state = hass.states.get("sensor.custom_name")
    assert state is not None
    assert state.name == "Custom Name"


@pytest.mark.parametrize(
    "prediction_results",
    (
        {},
        {"Error": "Failed"},
    ),
)
async def test_no_predictions(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_predictions: MagicMock,
    mock_nextbus_lists: MagicMock,
    prediction_results: dict[str, str],
) -> None:
    """Verify there are no exceptions when no predictions are returned."""
    mock_nextbus_predictions.return_value = prediction_results

    await assert_setup_sensor(hass, CONFIG_BASIC)

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.state == "unknown"


async def test_verify_no_upcoming(
    hass: HomeAssistant,
    mock_nextbus: MagicMock,
    mock_nextbus_lists: MagicMock,
    mock_nextbus_predictions: MagicMock,
) -> None:
    """Verify attributes are set despite no upcoming times."""
    mock_nextbus_predictions.return_value = {
        "predictions": {
            "agencyTitle": VALID_AGENCY_TITLE,
            "agencyTag": VALID_AGENCY,
            "routeTitle": VALID_ROUTE_TITLE,
            "routeTag": VALID_ROUTE,
            "stopTitle": VALID_STOP_TITLE,
            "stopTag": VALID_STOP,
            "direction": {"title": "Outbound", "prediction": []},
        }
    }

    await assert_setup_sensor(hass, CONFIG_BASIC)

    state = hass.states.get(SENSOR_ID_SHORT)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["upcoming"] == "No upcoming predictions"
