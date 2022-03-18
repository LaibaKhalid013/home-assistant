"""Test cases around the demo fan platform."""
import pytest

from homeassistant.components import fan
from homeassistant.components.demo.fan import (
    PRESET_MODE_AUTO,
    PRESET_MODE_ON,
    PRESET_MODE_SLEEP,
    PRESET_MODE_SMART,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.setup import async_setup_component

FULL_FAN_ENTITY_IDS = ["fan.living_room_fan", "fan.percentage_full_fan"]
FANS_WITH_PRESET_MODE_ONLY = ["fan.preset_only_limited_fan"]
LIMITED_AND_FULL_FAN_ENTITY_IDS = FULL_FAN_ENTITY_IDS + [
    "fan.ceiling_fan",
    "fan.percentage_limited_fan",
]
FANS_WITH_PRESET_MODES = FULL_FAN_ENTITY_IDS + [
    "fan.percentage_limited_fan",
]
PERCENTAGE_MODEL_FANS = ["fan.percentage_full_fan", "fan.percentage_limited_fan"]


@pytest.fixture(autouse=True)
async def setup_comp(hass):
    """Initialize components."""
    assert await async_setup_component(hass, fan.DOMAIN, {"fan": {"platform": "demo"}})
    await hass.async_block_till_done()


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_on(hass, fan_entity_id):
    """Test turning on the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_turn_on_with_speed_and_percentage(hass, fan_entity_id):
    """Test turning on the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 66},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 66},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 0},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODE_ONLY)
async def test_turn_on_with_preset_mode_only(hass, fan_entity_id):
    """Test turning on the device with a preset_mode and no speed setting."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PRESET_MODES] == [
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
        PRESET_MODE_SLEEP,
        PRESET_MODE_ON,
    ]

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_SMART},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_SMART

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert fan.ATTR_PRESET_MODE not in state.attributes

    with pytest.raises(ValueError):
        await hass.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
        await hass.async_block_till_done()

    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert fan.ATTR_PRESET_MODE not in state.attributes


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODES)
async def test_turn_on_with_preset_mode_and_speed(hass, fan_entity_id):
    """Test turning on the device with a preset_mode and speed."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert fan.ATTR_PERCENTAGE not in state.attributes
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PRESET_MODES] == [
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
        PRESET_MODE_SLEEP,
        PRESET_MODE_ON,
    ]

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100
    assert fan.ATTR_PRESET_MODE not in state.attributes

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_SMART},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert fan.ATTR_PERCENTAGE not in state.attributes
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_SMART

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert fan.ATTR_PRESET_MODE not in state.attributes

    with pytest.raises(ValueError):
        await hass.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
        await hass.async_block_till_done()

    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert fan.ATTR_PRESET_MODE not in state.attributes


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off(hass, fan_entity_id):
    """Test turning off the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off_without_entity_id(hass, fan_entity_id):
    """Test turning off all fans."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_direction(hass, fan_entity_id):
    """Test setting the direction of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_DIRECTION,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_DIRECTION: fan.DIRECTION_REVERSE},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_DIRECTION] == fan.DIRECTION_REVERSE


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODES)
async def test_set_preset_mode(hass, fan_entity_id):
    """Test setting the preset mode of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert fan.ATTR_PERCENTAGE not in state.attributes
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_set_preset_mode_invalid(hass, fan_entity_id):
    """Test setting a invalid preset mode for the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    with pytest.raises(ValueError):
        await hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
        await hass.async_block_till_done()

    with pytest.raises(ValueError):
        await hass.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
        await hass.async_block_till_done()


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_percentage(hass, fan_entity_id):
    """Test setting the percentage speed of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_increase_decrease_speed(hass, fan_entity_id):
    """Test increasing and decreasing the percentage speed of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE_STEP] == 100 / 3

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0


@pytest.mark.parametrize("fan_entity_id", PERCENTAGE_MODEL_FANS)
async def test_increase_decrease_speed_with_percentage_step(hass, fan_entity_id):
    """Test increasing speed with a percentage step."""
    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 25

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 50

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 75


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_oscillate(hass, fan_entity_id):
    """Test oscillating the fan."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert not state.attributes.get(fan.ATTR_OSCILLATING)

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: True},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is True

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: False},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is False


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_is_on(hass, fan_entity_id):
    """Test is on service call."""
    assert not fan.is_on(hass, fan_entity_id)

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    assert fan.is_on(hass, fan_entity_id)
