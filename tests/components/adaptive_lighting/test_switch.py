"""Tests for Adaptive Lighting switches."""
import datetime

import pytest

from homeassistant.components.adaptive_lighting.const import (
    ATTR_TURN_ON_OFF_LISTENER,
    CONF_INITIAL_TRANSITION,
    CONF_MANUAL_CONTROL,
    CONF_SUNRISE_TIME,
    CONF_SUNSET_TIME,
    CONF_TRANSITION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_NAME,
    DEFAULT_SLEEP_BRIGHTNESS,
    DEFAULT_SLEEP_COLOR_TEMP,
    DOMAIN,
    SERVICE_SET_MANUAL_CONTROL,
    UNDO_UPDATE_LISTENER,
)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
import homeassistant.config as config_util
from homeassistant.const import ATTR_ENTITY_ID, CONF_LIGHTS, CONF_NAME, SERVICE_TURN_ON
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util

from tests.async_mock import patch
from tests.common import MockConfigEntry
from tests.components.demo.test_light import ENTITY_LIGHT

SUNRISE = datetime.datetime(
    year=2020,
    month=10,
    day=17,
    hour=6,
)
SUNSET = datetime.datetime(
    year=2020,
    month=10,
    day=17,
    hour=22,
)

LAT_LONG_TZS = [
    (39, -1, "Europe/Madrid"),
    (60, 50, "GMT"),
    (55, 13, "Europe/Copenhagen"),
    (52.379189, 4.899431, "Europe/Amsterdam"),
    (32.87336, -117.22743, "US/Pacific"),
]

ENTITY_SLEEP_MODE_SWITCH = f"{SWITCH_DOMAIN}.{DOMAIN}_sleep_mode_{DEFAULT_NAME}"


async def setup_switch(hass, extra_data):
    """Create the switch entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_NAME: DEFAULT_NAME, **extra_data})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def setup_switch_and_lights(hass):
    """Create switch and demo lights."""
    # Setup demo lights and turn on
    await async_setup_component(
        hass, LIGHT_DOMAIN, {LIGHT_DOMAIN: [{"platform": "demo"}]}
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_LIGHT},
        blocking=True,
    )

    # Setup switch
    lights = [
        "light.bed_light",
        "light.ceiling_lights",
        "light.kitchen_lights",
    ]
    assert all(hass.states.get(light) is not None for light in lights)
    entry = await setup_switch(
        hass,
        {
            CONF_LIGHTS: lights,
            CONF_SUNRISE_TIME: datetime.time(SUNRISE.hour),
            CONF_SUNSET_TIME: datetime.time(SUNSET.hour),
            CONF_INITIAL_TRANSITION: 0,
            CONF_TRANSITION: 0,
        },
    )
    switch = hass.data[DOMAIN][entry.entry_id][SWITCH_DOMAIN]
    await hass.async_block_till_done()
    return switch


async def test_adaptive_lighting_switches(hass):
    """Test switches created for adaptive_lighting integration."""
    entry = await setup_switch(hass, {})

    assert len(hass.states.async_entity_ids(SWITCH_DOMAIN)) == 2
    assert hass.states.async_entity_ids(SWITCH_DOMAIN) == [
        f"{SWITCH_DOMAIN}.{DOMAIN}_{DEFAULT_NAME}",
        f"{SWITCH_DOMAIN}.{DOMAIN}_sleep_mode_{DEFAULT_NAME}",
    ]
    assert ATTR_TURN_ON_OFF_LISTENER in hass.data[DOMAIN]
    assert entry.entry_id in hass.data[DOMAIN]
    assert len(hass.data[DOMAIN].keys()) == 2

    data = hass.data[DOMAIN][entry.entry_id]
    assert "sleep_mode_switch" in data
    assert SWITCH_DOMAIN in data
    assert UNDO_UPDATE_LISTENER in data
    assert len(data.keys()) == 3


@pytest.mark.parametrize("lat,long,tz", LAT_LONG_TZS)
async def test_adaptive_lighting_time_zones_with_default_settings(hass, lat, long, tz):
    """Test setting up the Adaptive Lighting switches with different timezones."""
    await config_util.async_process_ha_core_config(
        hass,
        {"latitude": lat, "longitude": long, "time_zone": tz},
    )
    entry = await setup_switch(hass, {})
    switch = hass.data[DOMAIN][entry.entry_id][SWITCH_DOMAIN]
    # Shouldn't raise an exception ever
    await switch._update_attrs_and_maybe_adapt_lights(
        context=switch.create_context("test")
    )


@pytest.mark.parametrize("lat,long,tz", LAT_LONG_TZS)
async def test_adaptive_lighting_time_zones_and_sun_settings(hass, lat, long, tz):
    """Test setting up the Adaptive Lighting switches with different timezones.

    Also test the (sleep) brightness and color temperature settings.
    """
    await config_util.async_process_ha_core_config(
        hass,
        {"latitude": lat, "longitude": long, "time_zone": tz},
    )
    entry = await setup_switch(
        hass,
        {
            CONF_SUNRISE_TIME: datetime.time(SUNRISE.hour),
            CONF_SUNSET_TIME: datetime.time(SUNSET.hour),
        },
    )

    switch = hass.data[DOMAIN][entry.entry_id][SWITCH_DOMAIN]
    context = switch.create_context("test")  # needs to be passed to update method
    min_color_temp = switch._sun_light_settings.min_color_temp

    sunset = hass.config.time_zone.localize(SUNSET).astimezone(dt_util.UTC)
    before_sunset = sunset - datetime.timedelta(hours=1)
    after_sunset = sunset + datetime.timedelta(hours=1)
    sunrise = hass.config.time_zone.localize(SUNRISE).astimezone(dt_util.UTC)
    before_sunrise = sunrise - datetime.timedelta(hours=1)
    after_sunrise = sunrise + datetime.timedelta(hours=1)

    async def patch_time_and_update(time):
        with patch("homeassistant.util.dt.utcnow", return_value=time):
            await switch._update_attrs_and_maybe_adapt_lights(context=context)
            await hass.async_block_till_done()

    # At sunset the brightness should be max and color_temp at the smallest value
    await patch_time_and_update(sunset)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] == DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] == min_color_temp

    # One hour before sunset the brightness should be max and color_temp
    # not at the smallest value yet.
    await patch_time_and_update(before_sunset)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] == DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] > min_color_temp

    # One hour after sunset the brightness should be down
    await patch_time_and_update(after_sunset)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] < DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] == min_color_temp

    # At sunrise the brightness should be max and color_temp at the smallest value
    await patch_time_and_update(sunrise)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] == DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] == min_color_temp

    # One hour before sunrise the brightness should smaller than max
    # and color_temp at the min value.
    await patch_time_and_update(before_sunrise)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] < DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] == min_color_temp

    # One hour after sunrise the brightness should be up
    await patch_time_and_update(after_sunrise)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] == DEFAULT_MAX_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] > min_color_temp

    # Turn on sleep mode which make the brightness and color_temp
    # deterministic regardless of the time
    sleep_mode_switch = hass.data[DOMAIN][entry.entry_id]["sleep_mode_switch"]
    await sleep_mode_switch.async_turn_on()
    await switch._update_attrs_and_maybe_adapt_lights(context=context)
    assert switch._settings[ATTR_BRIGHTNESS_PCT] == DEFAULT_SLEEP_BRIGHTNESS
    assert switch._settings["color_temp_kelvin"] == DEFAULT_SLEEP_COLOR_TEMP


async def test_light_settings(hass):
    """Test that light settings are correctly applied."""
    switch = await setup_switch_and_lights(hass)
    lights = switch._lights

    # Turn on "sleep mode"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_SLEEP_MODE_SWITCH},
        blocking=True,
    )
    await hass.async_block_till_done()
    light_states = [hass.states.get(light) for light in lights]
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] == round(
            255 * switch._settings[ATTR_BRIGHTNESS_PCT] / 100
        )
        last_service_data = switch.turn_on_off_listener.last_service_data[
            state.entity_id
        ]
        assert state.attributes[ATTR_BRIGHTNESS] == last_service_data[ATTR_BRIGHTNESS]
        assert state.attributes[ATTR_COLOR_TEMP] == last_service_data[ATTR_COLOR_TEMP]

    # Turn off "sleep mode"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_SLEEP_MODE_SWITCH},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Test with different times
    sunset = hass.config.time_zone.localize(SUNSET).astimezone(dt_util.UTC)
    before_sunset = sunset - datetime.timedelta(hours=1)
    after_sunset = sunset + datetime.timedelta(hours=1)
    sunrise = hass.config.time_zone.localize(SUNRISE).astimezone(dt_util.UTC)
    before_sunrise = sunrise - datetime.timedelta(hours=1)
    after_sunrise = sunrise + datetime.timedelta(hours=1)

    context = switch.create_context("test")  # needs to be passed to update method

    async def patch_time_and_get_updated_states(time):
        with patch("homeassistant.util.dt.utcnow", return_value=time):
            await switch._update_attrs_and_maybe_adapt_lights(
                transition=0, context=context, force=True
            )
            await hass.async_block_till_done()
            return [hass.states.get(light) for light in lights]

    def assert_expected_color_temp(state):
        last_service_data = switch.turn_on_off_listener.last_service_data[
            state.entity_id
        ]
        assert state.attributes[ATTR_COLOR_TEMP] == last_service_data[ATTR_COLOR_TEMP]

    # At sunset the brightness should be max and color_temp at the smallest value
    light_states = await patch_time_and_get_updated_states(sunset)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] == 255
        assert_expected_color_temp(state)

    # One hour before sunset the brightness should be max and color_temp
    # not at the smallest value yet.
    light_states = await patch_time_and_get_updated_states(before_sunset)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] == 255
        assert_expected_color_temp(state)

    # One hour after sunset the brightness should be down
    light_states = await patch_time_and_get_updated_states(after_sunset)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] < 255
        assert_expected_color_temp(state)

    # At sunrise the brightness should be max and color_temp at the smallest value
    light_states = await patch_time_and_get_updated_states(sunrise)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] == 255
        assert_expected_color_temp(state)

    # One hour before sunrise the brightness should smaller than max
    # and color_temp at the min value.
    light_states = await patch_time_and_get_updated_states(before_sunrise)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] < 255
        assert_expected_color_temp(state)

    # One hour after sunrise the brightness should be up
    light_states = await patch_time_and_get_updated_states(after_sunrise)
    for state in light_states:
        assert state.attributes[ATTR_BRIGHTNESS] == 255
        assert_expected_color_temp(state)


async def test_manual_control(hass):
    """Test the 'manual control' tracking."""
    switch = await setup_switch_and_lights(hass)
    context = switch.create_context("test")  # needs to be passed to update method

    async def update():
        await switch._update_attrs_and_maybe_adapt_lights(transition=0, context=context)
        await hass.async_block_till_done()

    async def turn_light(state):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON if state else SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: ENTITY_LIGHT},
            blocking=True,
        )
        await hass.async_block_till_done()
        await update()

    async def change_manual_control(set_to):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_MANUAL_CONTROL,
            {
                ATTR_ENTITY_ID: switch.entity_id,
                CONF_MANUAL_CONTROL: set_to,
                CONF_LIGHTS: [ENTITY_LIGHT],
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        await update()

    # Nothing is manually controlled
    await update()
    assert not switch.turn_on_off_listener.manual_control[ENTITY_LIGHT]
    # Call light.turn_on for ENTITY_LIGHT
    await turn_light(True)
    # Check that ENTITY_LIGHT is manually controlled
    assert switch.turn_on_off_listener.manual_control[ENTITY_LIGHT]
    # Test adaptive_lighting.set_manual_control
    await change_manual_control(False)
    # Check that ENTITY_LIGHT is not manually controlled
    assert not switch.turn_on_off_listener.manual_control[ENTITY_LIGHT]

    # Check that changing light on and off removes manual control
    await change_manual_control(True)
    await turn_light(True)  # is already on
    assert switch.turn_on_off_listener.manual_control[ENTITY_LIGHT]
    await turn_light(False)
    await turn_light(True)
    assert not switch.turn_on_off_listener.manual_control[ENTITY_LIGHT]
