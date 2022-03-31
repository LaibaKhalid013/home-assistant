"""The test for the HERE Travel Time sensor platform."""
from unittest.mock import MagicMock, patch

from herepy.here_enum import RouteMode
from herepy.routing_api import NoRouteFoundError
import pytest

from homeassistant.components.here_travel_time.const import (
    ATTR_DESTINATION,
    ATTR_DESTINATION_NAME,
    ATTR_DISTANCE,
    ATTR_DURATION,
    ATTR_DURATION_IN_TRAFFIC,
    ATTR_ORIGIN,
    ATTR_ORIGIN_NAME,
    ATTR_ROUTE,
    CONF_DESTINATION,
    CONF_ORIGIN,
    CONF_ROUTE_MODE,
    CONF_TIME,
    CONF_TIME_TYPE,
    CONF_TRAFFIC_MODE,
    CONF_UNIT_SYSTEM,
    DEPARTURE_TIME,
    DOMAIN,
    ICON_BICYCLE,
    ICON_CAR,
    ICON_PEDESTRIAN,
    ICON_PUBLIC,
    ICON_TRUCK,
    NO_ROUTE_ERROR_MESSAGE,
    ROUTE_MODE_FASTEST,
    TRAFFIC_MODE_DISABLED,
    TRAFFIC_MODE_ENABLED,
    TRAVEL_MODE_BICYCLE,
    TRAVEL_MODE_CAR,
    TRAVEL_MODE_PEDESTRIAN,
    TRAVEL_MODE_PUBLIC_TIME_TABLE,
    TRAVEL_MODE_TRUCK,
    TRAVEL_MODES_VEHICLE,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_ICON,
    CONF_API_KEY,
    CONF_MODE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
    TIME_MINUTES,
)
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util

from .const import (
    API_KEY,
    CAR_DESTINATION_LATITUDE,
    CAR_DESTINATION_LONGITUDE,
    CAR_ORIGIN_LATITUDE,
    CAR_ORIGIN_LONGITUDE,
)

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    "mode,icon,traffic_mode,unit_system,expected_state,expected_distance,expected_duration_in_traffic",
    [
        (
            TRAVEL_MODE_CAR,
            ICON_CAR,
            TRAFFIC_MODE_ENABLED,
            "metric",
            "31",
            23.903,
            31.016666666666666,
        ),
        (
            TRAVEL_MODE_BICYCLE,
            ICON_BICYCLE,
            TRAFFIC_MODE_DISABLED,
            "metric",
            "30",
            23.903,
            30.05,
        ),
        (
            TRAVEL_MODE_PEDESTRIAN,
            ICON_PEDESTRIAN,
            TRAFFIC_MODE_DISABLED,
            "imperial",
            "30",
            14.852635608048994,
            30.05,
        ),
        (
            TRAVEL_MODE_PUBLIC_TIME_TABLE,
            ICON_PUBLIC,
            TRAFFIC_MODE_DISABLED,
            "imperial",
            "30",
            14.852635608048994,
            30.05,
        ),
        (
            TRAVEL_MODE_TRUCK,
            ICON_TRUCK,
            TRAFFIC_MODE_ENABLED,
            "metric",
            "31",
            23.903,
            31.016666666666666,
        ),
    ],
)
async def test_sensor(
    hass,
    mode,
    icon,
    traffic_mode,
    unit_system,
    expected_state,
    expected_distance,
    expected_duration_in_traffic,
    valid_response,
):
    """Test that sensor works."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0123456789",
        data={
            CONF_ORIGIN: f"{CAR_ORIGIN_LATITUDE},{CAR_ORIGIN_LONGITUDE}",
            CONF_DESTINATION: f"{CAR_DESTINATION_LATITUDE},{CAR_DESTINATION_LONGITUDE}",
            CONF_API_KEY: API_KEY,
            CONF_MODE: mode,
            CONF_NAME: "test",
        },
        options={
            CONF_TRAFFIC_MODE: traffic_mode,
            CONF_ROUTE_MODE: ROUTE_MODE_FASTEST,
            CONF_TIME_TYPE: DEPARTURE_TIME,
            CONF_TIME: None,
            CONF_UNIT_SYSTEM: unit_system,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.test")
    assert sensor.attributes.get("unit_of_measurement") == TIME_MINUTES
    assert (
        sensor.attributes.get(ATTR_ATTRIBUTION)
        == "With the support of HERE Technologies. All information is provided without warranty of any kind."
    )
    assert sensor.state == expected_state

    assert sensor.attributes.get(ATTR_DURATION) == 30.05
    assert sensor.attributes.get(ATTR_DISTANCE) == expected_distance
    assert sensor.attributes.get(ATTR_ROUTE) == (
        "US-29 - K St NW; US-29 - Whitehurst Fwy; "
        "I-495 N - Capital Beltway; MD-187 S - Old Georgetown Rd"
    )
    assert sensor.attributes.get(CONF_UNIT_SYSTEM) == unit_system
    assert (
        sensor.attributes.get(ATTR_DURATION_IN_TRAFFIC) == expected_duration_in_traffic
    )
    assert sensor.attributes.get(ATTR_ORIGIN) == ",".join(
        [CAR_ORIGIN_LATITUDE, CAR_ORIGIN_LONGITUDE]
    )
    assert sensor.attributes.get(ATTR_DESTINATION) == ",".join(
        [CAR_DESTINATION_LATITUDE, CAR_DESTINATION_LONGITUDE]
    )
    assert sensor.attributes.get(ATTR_ORIGIN_NAME) == "22nd St NW"
    assert sensor.attributes.get(ATTR_DESTINATION_NAME) == "Service Rd S"
    assert sensor.attributes.get(CONF_MODE) == mode
    assert sensor.attributes.get(CONF_TRAFFIC_MODE) is (
        traffic_mode == TRAFFIC_MODE_ENABLED
    )

    assert sensor.attributes.get(ATTR_ICON) == icon

    # Test traffic mode disabled for vehicles
    if mode in TRAVEL_MODES_VEHICLE:
        assert sensor.attributes.get(ATTR_DURATION) != sensor.attributes.get(
            ATTR_DURATION_IN_TRAFFIC
        )


async def test_entity_ids(hass, valid_response: MagicMock):
    """Test that origin/destination supplied by entities works."""
    utcnow = dt_util.utcnow()
    # Patching 'utcnow' to gain more control over the timed update.
    with patch("homeassistant.util.dt.utcnow", return_value=utcnow):
        zone_config = {
            "zone": [
                {
                    "name": "Origin",
                    "latitude": CAR_ORIGIN_LATITUDE,
                    "longitude": CAR_ORIGIN_LONGITUDE,
                    "radius": 250,
                    "passive": False,
                },
            ]
        }
        assert await async_setup_component(hass, "zone", zone_config)
        hass.states.async_set(
            "device_tracker.test",
            "not_home",
            {
                "latitude": float(CAR_DESTINATION_LATITUDE),
                "longitude": float(CAR_DESTINATION_LONGITUDE),
            },
        )
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="0123456789",
            data={
                CONF_ORIGIN: "zone.origin",
                CONF_DESTINATION: "device_tracker.test",
                CONF_API_KEY: API_KEY,
                CONF_MODE: TRAVEL_MODE_TRUCK,
                CONF_NAME: "test",
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
        await hass.async_block_till_done()

        sensor = hass.states.get("sensor.test")
        assert sensor.attributes.get(ATTR_DISTANCE) == 23.903

        valid_response.assert_called_with(
            [CAR_ORIGIN_LATITUDE, CAR_ORIGIN_LONGITUDE],
            [CAR_DESTINATION_LATITUDE, CAR_DESTINATION_LONGITUDE],
            True,
            [
                RouteMode[ROUTE_MODE_FASTEST],
                RouteMode[TRAVEL_MODE_TRUCK],
                RouteMode[TRAFFIC_MODE_ENABLED],
            ],
            arrival=None,
            departure="now",
        )


async def test_destination_entity_not_found(hass, caplog, valid_response: MagicMock):
    """Test that a not existing destination_entity_id is caught."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0123456789",
        data={
            CONF_ORIGIN: f"{CAR_ORIGIN_LATITUDE}, {CAR_ORIGIN_LONGITUDE}",
            CONF_DESTINATION: "device_tracker.test",
            CONF_API_KEY: API_KEY,
            CONF_MODE: TRAVEL_MODE_TRUCK,
            CONF_NAME: "test",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    assert "device_tracker.test are not valid coordinates" in caplog.text


async def test_origin_entity_not_found(hass, caplog, valid_response: MagicMock):
    """Test that a not existing origin_entity_id is caught."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0123456789",
        data={
            CONF_ORIGIN: "device_tracker.test",
            CONF_DESTINATION: f"{CAR_ORIGIN_LATITUDE}, {CAR_ORIGIN_LONGITUDE}",
            CONF_API_KEY: API_KEY,
            CONF_MODE: TRAVEL_MODE_TRUCK,
            CONF_NAME: "test",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    assert "device_tracker.test are not valid coordinates" in caplog.text


async def test_invalid_destination_entity_state(
    hass, caplog, valid_response: MagicMock
):
    """Test that an invalid state of the destination_entity_id is caught."""
    hass.states.async_set(
        "device_tracker.test",
        "test_state",
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0123456789",
        data={
            CONF_ORIGIN: f"{CAR_ORIGIN_LATITUDE}, {CAR_ORIGIN_LONGITUDE}",
            CONF_DESTINATION: "device_tracker.test",
            CONF_API_KEY: API_KEY,
            CONF_MODE: TRAVEL_MODE_TRUCK,
            CONF_NAME: "test",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    assert "test_state are not valid coordinates" in caplog.text


async def test_invalid_origin_entity_state(hass, caplog, valid_response: MagicMock):
    """Test that an invalid state of the origin_entity_id is caught."""
    hass.states.async_set(
        "device_tracker.test",
        "test_state",
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0123456789",
        data={
            CONF_ORIGIN: "device_tracker.test",
            CONF_DESTINATION: f"{CAR_ORIGIN_LATITUDE}, {CAR_ORIGIN_LONGITUDE}",
            CONF_API_KEY: API_KEY,
            CONF_MODE: TRAVEL_MODE_TRUCK,
            CONF_NAME: "test",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    assert "test_state are not valid coordinates" in caplog.text


async def test_route_not_found(hass, caplog):
    """Test that route not found error is correctly handled."""
    with patch(
        "homeassistant.components.here_travel_time.config_flow.validate_input",
        return_value=None,
    ), patch(
        "herepy.RoutingApi.public_transport_timetable",
        side_effect=NoRouteFoundError,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="0123456789",
            data={
                CONF_ORIGIN: f"{CAR_ORIGIN_LATITUDE},{CAR_ORIGIN_LONGITUDE}",
                CONF_DESTINATION: f"{CAR_DESTINATION_LATITUDE},{CAR_DESTINATION_LONGITUDE}",
                CONF_API_KEY: API_KEY,
                CONF_MODE: TRAVEL_MODE_TRUCK,
                CONF_NAME: "test",
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
        await hass.async_block_till_done()

        assert NO_ROUTE_ERROR_MESSAGE in caplog.text


async def test_setup_platform(hass, caplog):
    """Test that setup platform migration works."""
    config = {
        "sensor": {
            "platform": DOMAIN,
            "name": "test",
            "origin_latitude": CAR_ORIGIN_LATITUDE,
            "origin_longitude": CAR_ORIGIN_LONGITUDE,
            "destination_latitude": CAR_DESTINATION_LATITUDE,
            "destination_longitude": CAR_DESTINATION_LONGITUDE,
            "api_key": API_KEY,
        }
    }
    with patch(
        "homeassistant.components.here_travel_time.async_setup_entry", return_value=True
    ):
        await async_setup_component(hass, "sensor", config)
        await hass.async_block_till_done()
        assert (
            "Your HERE travel time configuration has been imported into the UI"
            in caplog.text
        )
