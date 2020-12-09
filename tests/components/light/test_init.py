"""The tests for the Light component."""
import pytest
import voluptuous as vol

from homeassistant import core
from homeassistant.components import light
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_PLATFORM,
    ENTITY_MATCH_ALL,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.exceptions import Unauthorized
from homeassistant.setup import async_setup_component

from tests.async_mock import MagicMock, mock_open, patch
from tests.common import async_mock_service

orig_Profiles = light.Profiles


async def test_methods(hass):
    """Test if methods call the services as expected."""
    # Test is_on
    hass.states.async_set("light.test", STATE_ON)
    assert light.is_on(hass, "light.test")

    hass.states.async_set("light.test", STATE_OFF)
    assert not light.is_on(hass, "light.test")

    # Test turn_on
    turn_on_calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "entity_id_val",
            light.ATTR_TRANSITION: "transition_val",
            light.ATTR_BRIGHTNESS: "brightness_val",
            light.ATTR_RGB_COLOR: "rgb_color_val",
            light.ATTR_XY_COLOR: "xy_color_val",
            light.ATTR_PROFILE: "profile_val",
            light.ATTR_COLOR_NAME: "color_name_val",
            light.ATTR_WHITE_VALUE: "white_val",
        },
        blocking=True,
    )

    assert len(turn_on_calls) == 1
    call = turn_on_calls[-1]

    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "entity_id_val"
    assert call.data.get(light.ATTR_TRANSITION) == "transition_val"
    assert call.data.get(light.ATTR_BRIGHTNESS) == "brightness_val"
    assert call.data.get(light.ATTR_RGB_COLOR) == "rgb_color_val"
    assert call.data.get(light.ATTR_XY_COLOR) == "xy_color_val"
    assert call.data.get(light.ATTR_PROFILE) == "profile_val"
    assert call.data.get(light.ATTR_COLOR_NAME) == "color_name_val"
    assert call.data.get(light.ATTR_WHITE_VALUE) == "white_val"

    # Test turn_off
    turn_off_calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_OFF)

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "entity_id_val",
            light.ATTR_TRANSITION: "transition_val",
        },
        blocking=True,
    )

    assert len(turn_off_calls) == 1
    call = turn_off_calls[-1]

    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data[ATTR_ENTITY_ID] == "entity_id_val"
    assert call.data[light.ATTR_TRANSITION] == "transition_val"

    # Test toggle
    toggle_calls = async_mock_service(hass, light.DOMAIN, SERVICE_TOGGLE)

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: "entity_id_val", light.ATTR_TRANSITION: "transition_val"},
        blocking=True,
    )

    assert len(toggle_calls) == 1
    call = toggle_calls[-1]

    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TOGGLE
    assert call.data[ATTR_ENTITY_ID] == "entity_id_val"
    assert call.data[light.ATTR_TRANSITION] == "transition_val"


async def test_services(hass, mock_light_profiles):
    """Test the provided services."""
    platform = getattr(hass.components, "test.light")

    platform.init()
    assert await async_setup_component(
        hass, light.DOMAIN, {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await hass.async_block_till_done()

    ent1, ent2, ent3 = platform.ENTITIES

    # Test init
    assert light.is_on(hass, ent1.entity_id)
    assert not light.is_on(hass, ent2.entity_id)
    assert not light.is_on(hass, ent3.entity_id)

    # Test basic turn_on, turn_off, toggle services
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ent1.entity_id}, blocking=True
    )
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ent2.entity_id}, blocking=True
    )

    assert not light.is_on(hass, ent1.entity_id)
    assert light.is_on(hass, ent2.entity_id)

    # turn on all lights
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )

    assert light.is_on(hass, ent1.entity_id)
    assert light.is_on(hass, ent2.entity_id)
    assert light.is_on(hass, ent3.entity_id)

    # turn off all lights
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )

    assert not light.is_on(hass, ent1.entity_id)
    assert not light.is_on(hass, ent2.entity_id)
    assert not light.is_on(hass, ent3.entity_id)

    # turn off all lights by setting brightness to 0
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL, light.ATTR_BRIGHTNESS: 0},
        blocking=True,
    )

    assert not light.is_on(hass, ent1.entity_id)
    assert not light.is_on(hass, ent2.entity_id)
    assert not light.is_on(hass, ent3.entity_id)

    # toggle all lights
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )

    assert light.is_on(hass, ent1.entity_id)
    assert light.is_on(hass, ent2.entity_id)
    assert light.is_on(hass, ent3.entity_id)

    # toggle all lights
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )

    assert not light.is_on(hass, ent1.entity_id)
    assert not light.is_on(hass, ent2.entity_id)
    assert not light.is_on(hass, ent3.entity_id)

    # Ensure all attributes process correctly
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent1.entity_id,
            light.ATTR_TRANSITION: 10,
            light.ATTR_BRIGHTNESS: 20,
            light.ATTR_COLOR_NAME: "blue",
        },
        blocking=True,
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent2.entity_id,
            light.ATTR_RGB_COLOR: (255, 255, 255),
            light.ATTR_WHITE_VALUE: 255,
        },
        blocking=True,
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent3.entity_id,
            light.ATTR_XY_COLOR: (0.4, 0.6),
        },
        blocking=True,
    )

    _, data = ent1.last_call("turn_on")
    assert data == {
        light.ATTR_TRANSITION: 10,
        light.ATTR_BRIGHTNESS: 20,
        light.ATTR_HS_COLOR: (240, 100),
    }

    _, data = ent2.last_call("turn_on")
    assert data == {light.ATTR_HS_COLOR: (0, 0), light.ATTR_WHITE_VALUE: 255}

    _, data = ent3.last_call("turn_on")
    assert data == {light.ATTR_HS_COLOR: (71.059, 100)}

    # Ensure attributes are filtered when light is turned off
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent1.entity_id,
            light.ATTR_TRANSITION: 10,
            light.ATTR_BRIGHTNESS: 0,
            light.ATTR_COLOR_NAME: "blue",
        },
        blocking=True,
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent2.entity_id,
            light.ATTR_BRIGHTNESS: 0,
            light.ATTR_RGB_COLOR: (255, 255, 255),
            light.ATTR_WHITE_VALUE: 0,
        },
        blocking=True,
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent3.entity_id,
            light.ATTR_BRIGHTNESS: 0,
            light.ATTR_XY_COLOR: (0.4, 0.6),
        },
        blocking=True,
    )

    assert not light.is_on(hass, ent1.entity_id)
    assert not light.is_on(hass, ent2.entity_id)
    assert not light.is_on(hass, ent3.entity_id)

    _, data = ent1.last_call("turn_off")
    assert data == {light.ATTR_TRANSITION: 10}

    _, data = ent2.last_call("turn_off")
    assert data == {}

    _, data = ent3.last_call("turn_off")
    assert data == {}

    # One of the light profiles
    profile = light.Profile("relax", 0.513, 0.413, 144, 0)
    mock_light_profiles[profile.name] = profile

    # Test light profiles
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ent1.entity_id, light.ATTR_PROFILE: profile.name},
        blocking=True,
    )
    # Specify a profile and a brightness attribute to overwrite it
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent2.entity_id,
            light.ATTR_PROFILE: profile.name,
            light.ATTR_BRIGHTNESS: 100,
            light.ATTR_TRANSITION: 1,
        },
        blocking=True,
    )

    _, data = ent1.last_call("turn_on")
    assert data == {
        light.ATTR_BRIGHTNESS: profile.brightness,
        light.ATTR_HS_COLOR: profile.hs_color,
        light.ATTR_TRANSITION: profile.transition,
    }

    _, data = ent2.last_call("turn_on")
    assert data == {
        light.ATTR_BRIGHTNESS: 100,
        light.ATTR_HS_COLOR: profile.hs_color,
        light.ATTR_TRANSITION: 1,
    }

    # Test toggle with parameters
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TOGGLE,
        {
            ATTR_ENTITY_ID: ent3.entity_id,
            light.ATTR_PROFILE: profile.name,
            light.ATTR_BRIGHTNESS_PCT: 100,
        },
        blocking=True,
    )

    _, data = ent3.last_call("turn_on")
    assert data == {
        light.ATTR_BRIGHTNESS: 255,
        light.ATTR_HS_COLOR: profile.hs_color,
        light.ATTR_TRANSITION: profile.transition,
    }

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TOGGLE,
        {
            ATTR_ENTITY_ID: ent3.entity_id,
            light.ATTR_TRANSITION: 4,
        },
        blocking=True,
    )

    _, data = ent3.last_call("turn_off")
    assert data == {
        light.ATTR_TRANSITION: 4,
    }

    # Test bad data
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ent1.entity_id, light.ATTR_PROFILE: -1},
        blocking=True,
    )
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ent2.entity_id, light.ATTR_XY_COLOR: ["bla-di-bla", 5]},
            blocking=True,
        )
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ent3.entity_id, light.ATTR_RGB_COLOR: [255, None, 2]},
            blocking=True,
        )

    _, data = ent1.last_call("turn_on")
    assert data == {}

    _, data = ent2.last_call("turn_on")
    assert data == {}

    _, data = ent3.last_call("turn_on")
    assert data == {}

    # faulty attributes will not trigger a service call
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: ent1.entity_id,
                light.ATTR_PROFILE: profile.name,
                light.ATTR_BRIGHTNESS: "bright",
            },
            blocking=True,
        )
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: ent1.entity_id,
                light.ATTR_RGB_COLOR: "yellowish",
            },
            blocking=True,
        )
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ent2.entity_id, light.ATTR_WHITE_VALUE: "high"},
            blocking=True,
        )

    _, data = ent1.last_call("turn_on")
    assert data == {}

    _, data = ent2.last_call("turn_on")
    assert data == {}


async def test_light_profiles(hass, mock_light_profiles):
    """Test light profiles."""
    platform = getattr(hass.components, "test.light")
    platform.init()

    profile = light.Profile("test", 0.4, 0.6, 100, 0)
    mock_light_profiles[profile.name] = profile
    profile = light.Profile("no color", None, None, 100, 0)
    mock_light_profiles[profile.name] = profile
    profile = light.Profile("test_off", 0, 0, 0, 0)
    mock_light_profiles[profile.name] = profile
    profile = light.Profile("no brightness", 0.4, 0.6, None)
    mock_light_profiles[profile.name] = profile

    assert await async_setup_component(
        hass, light.DOMAIN, {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await hass.async_block_till_done()

    ent1, _, _ = platform.ENTITIES

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent1.entity_id,
            light.ATTR_PROFILE: "test",
        },
        blocking=True,
    )

    _, data = ent1.last_call("turn_on")
    assert light.is_on(hass, ent1.entity_id)
    assert data == {
        light.ATTR_HS_COLOR: (71.059, 100),
        light.ATTR_BRIGHTNESS: 100,
        light.ATTR_TRANSITION: 0,
    }

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent1.entity_id,
            light.ATTR_PROFILE: "no color",
        },
        blocking=True,
    )

    _, data = ent1.last_call("turn_on")
    assert light.is_on(hass, ent1.entity_id)
    assert data == {
        light.ATTR_BRIGHTNESS: 100,
        light.ATTR_TRANSITION: 0,
    }

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ent1.entity_id, light.ATTR_PROFILE: "test_off"},
        blocking=True,
    )

    _, data = ent1.last_call("turn_off")
    assert not light.is_on(hass, ent1.entity_id)
    assert data == {light.ATTR_TRANSITION: 0}

    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ent1.entity_id,
            light.ATTR_PROFILE: "no brightness",
        },
        blocking=True,
    )

    _, data = ent1.last_call("turn_on")
    assert light.is_on(hass, ent1.entity_id)
    assert data == {
        light.ATTR_HS_COLOR: (71.059, 100),
        light.ATTR_TRANSITION: 0,
    }


async def test_default_profiles_group(hass, mock_light_profiles):
    """Test default turn-on light profile for all lights."""
    platform = getattr(hass.components, "test.light")
    platform.init()

    assert await async_setup_component(
        hass, light.DOMAIN, {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await hass.async_block_till_done()

    profile = light.Profile("group.all_lights.default", 0.4, 0.6, 99, 2)
    mock_light_profiles[profile.name] = profile

    ent, _, _ = platform.ENTITIES
    await hass.services.async_call(
        light.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ent.entity_id}, blocking=True
    )

    _, data = ent.last_call("turn_on")
    assert data == {
        light.ATTR_HS_COLOR: (71.059, 100),
        light.ATTR_BRIGHTNESS: 99,
        light.ATTR_TRANSITION: 2,
    }


async def test_default_profiles_light(hass, mock_light_profiles):
    """Test default turn-on light profile for a specific light."""
    platform = getattr(hass.components, "test.light")
    platform.init()

    assert await async_setup_component(
        hass, light.DOMAIN, {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await hass.async_block_till_done()

    profile = light.Profile("group.all_lights.default", 0.3, 0.5, 200, 0)
    mock_light_profiles[profile.name] = profile
    profile = light.Profile("light.ceiling_2.default", 0.6, 0.6, 100, 3)
    mock_light_profiles[profile.name] = profile

    dev = next(filter(lambda x: x.entity_id == "light.ceiling_2", platform.ENTITIES))
    await hass.services.async_call(
        light.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: dev.entity_id,
        },
        blocking=True,
    )

    _, data = dev.last_call("turn_on")
    assert data == {
        light.ATTR_HS_COLOR: (50.353, 100),
        light.ATTR_BRIGHTNESS: 100,
        light.ATTR_TRANSITION: 3,
    }


async def test_light_context(hass, hass_admin_user):
    """Test that light context works."""
    platform = getattr(hass.components, "test.light")
    platform.init()
    assert await async_setup_component(hass, "light", {"light": {"platform": "test"}})
    await hass.async_block_till_done()

    state = hass.states.get("light.ceiling")
    assert state is not None

    await hass.services.async_call(
        "light",
        "toggle",
        {"entity_id": state.entity_id},
        blocking=True,
        context=core.Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("light.ceiling")
    assert state2 is not None
    assert state.state != state2.state
    assert state2.context.user_id == hass_admin_user.id


async def test_light_turn_on_auth(hass, hass_admin_user):
    """Test that light context works."""
    platform = getattr(hass.components, "test.light")
    platform.init()
    assert await async_setup_component(hass, "light", {"light": {"platform": "test"}})
    await hass.async_block_till_done()

    state = hass.states.get("light.ceiling")
    assert state is not None

    hass_admin_user.mock_policy({})

    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": state.entity_id},
            blocking=True,
            context=core.Context(user_id=hass_admin_user.id),
        )


async def test_light_brightness_step(hass):
    """Test that light context works."""
    platform = getattr(hass.components, "test.light")
    platform.init()
    entity = platform.ENTITIES[0]
    entity.supported_features = light.SUPPORT_BRIGHTNESS
    entity.brightness = 100
    assert await async_setup_component(hass, "light", {"light": {"platform": "test"}})
    await hass.async_block_till_done()

    state = hass.states.get(entity.entity_id)
    assert state is not None
    assert state.attributes["brightness"] == 100

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_step": -10},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 90, data

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_step_pct": 10},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 126, data


async def test_light_brightness_pct_conversion(hass):
    """Test that light brightness percent conversion."""
    platform = getattr(hass.components, "test.light")
    platform.init()
    entity = platform.ENTITIES[0]
    entity.supported_features = light.SUPPORT_BRIGHTNESS
    entity.brightness = 100
    assert await async_setup_component(hass, "light", {"light": {"platform": "test"}})
    await hass.async_block_till_done()

    state = hass.states.get(entity.entity_id)
    assert state is not None
    assert state.attributes["brightness"] == 100

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_pct": 1},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 3, data

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_pct": 2},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 5, data

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_pct": 50},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 128, data

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_pct": 99},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 252, data

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity.entity_id, "brightness_pct": 100},
        blocking=True,
    )

    _, data = entity.last_call("turn_on")
    assert data["brightness"] == 255, data


def test_deprecated_base_class(caplog):
    """Test deprecated base class."""

    class CustomLight(light.Light):
        pass

    CustomLight()
    assert "Light is deprecated, modify CustomLight" in caplog.text


async def test_profiles(hass):
    """Test profiles loading."""
    profiles = orig_Profiles(hass)
    await profiles.async_initialize()
    assert profiles.data == {
        "concentrate": light.Profile("concentrate", 0.5119, 0.4147, 219, 0),
        "energize": light.Profile("energize", 0.368, 0.3686, 203, 0),
        "reading": light.Profile("reading", 0.4448, 0.4066, 240, 0),
        "relax": light.Profile("relax", 0.5119, 0.4147, 144, 0),
    }
    assert profiles.data["concentrate"].hs_color == (35.932, 69.412)
    assert profiles.data["energize"].hs_color == (43.333, 21.176)
    assert profiles.data["reading"].hs_color == (38.88, 49.02)
    assert profiles.data["relax"].hs_color == (35.932, 69.412)


@patch("os.path.isfile", MagicMock(side_effect=(True, False)))
async def test_profile_load_optional_hs_color(hass):
    """Test profile loading with profiles containing no xy color."""

    csv_file = """the first line is skipped
no_color,,,100,1
no_color_no_transition,,,110
color,0.5119,0.4147,120,2
color_no_transition,0.4448,0.4066,130
only_brightness,,,140
only_transition,,,,150
invalid_profile_1,
invalid_color_2,,0.1,1,2
invalid_color_3,,0.1,1
invalid_color_4,0.1,,1,3
invalid_color_5,0.1,,1
invalid_brightness,0,0,256,4
invalid_brightness_2,0,0,256
invalid_no_brightness_no_color_no_transition,,,
"""

    profiles = orig_Profiles(hass)
    with patch("builtins.open", mock_open(read_data=csv_file)):
        await profiles.async_initialize()
        await hass.async_block_till_done()

    assert profiles.data["no_color"].hs_color is None
    assert profiles.data["no_color"].brightness == 100
    assert profiles.data["no_color"].transition == 1

    assert profiles.data["no_color_no_transition"].hs_color is None
    assert profiles.data["no_color_no_transition"].brightness == 110
    assert profiles.data["no_color_no_transition"].transition == 0

    assert profiles.data["color"].hs_color == (35.932, 69.412)
    assert profiles.data["color"].brightness == 120
    assert profiles.data["color"].transition == 2

    assert profiles.data["color_no_transition"].hs_color == (38.88, 49.02)
    assert profiles.data["color_no_transition"].brightness == 130
    assert profiles.data["color_no_transition"].transition == 0

    assert profiles.data["only_brightness"].hs_color is None
    assert profiles.data["only_brightness"].brightness == 140
    assert profiles.data["only_brightness"].transition == 0

    assert profiles.data["only_transition"].hs_color is None
    assert profiles.data["only_transition"].brightness is None
    assert profiles.data["only_transition"].transition == 150

    for invalid_profile_name in (
        "invalid_profile_1",
        "invalid_color_2",
        "invalid_color_3",
        "invalid_color_4",
        "invalid_color_5",
        "invalid_brightness",
        "invalid_brightness_2",
        "invalid_no_brightness_no_color_no_transition",
    ):
        assert invalid_profile_name not in profiles.data
