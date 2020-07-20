"""The tests for the Rfxtrx sensor platform."""
from homeassistant.setup import async_setup_component

from . import _signal_event

EVENT_SMOKE_DETECTOR_PANIC = "08200300a109000670"
EVENT_SMOKE_DETECTOR_NO_PANIC = "08200300a109000770"

EVENT_MOTION_DETECTOR_MOTION = "08200100a109000470"
EVENT_MOTION_DETECTOR_NO_MOTION = "08200100a109000570"

EVENT_LIGHT_DETECTOR_LIGHT = "08200100a109001570"
EVENT_LIGHT_DETECTOR_DARK = "08200100a109001470"


async def test_one(hass, rfxtrx):
    """Test with 1 sensor."""
    assert await async_setup_component(
        hass,
        "rfxtrx",
        {"rfxtrx": {"device": "abcd", "devices": {"0b1100cd0213c7f230010f71": {}}}},
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.ac_213c7f2_48")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "AC 213c7f2:48"


async def test_one_pt2262(hass, rfxtrx):
    """Test with 1 sensor."""
    assert await async_setup_component(
        hass,
        "rfxtrx",
        {
            "rfxtrx": {
                "device": "abcd",
                "devices": {
                    "0913000022670e013970": {
                        "data_bits": 4,
                        "command_on": 0xE,
                        "command_off": 0x7,
                    }
                },
            }
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get("binary_sensor.pt2262_22670e")
    assert state
    assert state.state == "off"  # probably aught to be unknown
    assert state.attributes.get("friendly_name") == "PT2262 22670e"

    await _signal_event(hass, "0913000022670e013970")
    state = hass.states.get("binary_sensor.pt2262_22670e")
    assert state.state == "on"

    await _signal_event(hass, "09130000226707013d70")
    state = hass.states.get("binary_sensor.pt2262_22670e")
    assert state.state == "off"


async def test_several(hass, rfxtrx):
    """Test with 3."""
    assert await async_setup_component(
        hass,
        "rfxtrx",
        {
            "rfxtrx": {
                "device": "abcd",
                "devices": {
                    "0b1100cd0213c7f230010f71": {},
                    "0b1100100118cdea02010f70": {},
                    "0b1100101118cdea02010f70": {},
                },
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.ac_213c7f2_48")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "AC 213c7f2:48"

    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "AC 118cdea:2"

    state = hass.states.get("binary_sensor.ac_1118cdea_2")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "AC 1118cdea:2"


async def test_discover(hass, rfxtrx_automatic):
    """Test with discovery."""
    await _signal_event(hass, "0b1100100118cdea02010f70")
    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "on"

    await _signal_event(hass, "0b1100100118cdeb02010f70")
    state = hass.states.get("binary_sensor.ac_118cdeb_2")
    assert state
    assert state.state == "on"


async def test_off_delay(hass, rfxtrx, timestep):
    """Test with discovery."""
    assert await async_setup_component(
        hass,
        "rfxtrx",
        {
            "rfxtrx": {
                "device": "abcd",
                "devices": {"0b1100100118cdea02010f70": {"off_delay": 5}},
            }
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "off"

    await _signal_event(hass, "0b1100100118cdea02010f70")
    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "on"

    await timestep(4)
    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "on"

    await timestep(4)
    state = hass.states.get("binary_sensor.ac_118cdea_2")
    assert state
    assert state.state == "off"


async def test_panic(hass, rfxtrx_automatic):
    """Test panic entities."""

    entity_id = "binary_sensor.kd101_smoke_detector_a10900_32"

    await _signal_event(hass, EVENT_SMOKE_DETECTOR_PANIC)
    assert hass.states.get(entity_id).state == "on"
    assert hass.states.get(entity_id).attributes.get("device_class") == "smoke"

    await _signal_event(hass, EVENT_SMOKE_DETECTOR_NO_PANIC)
    assert hass.states.get(entity_id).state == "off"


async def test_panic_delay_off(hass, rfxtrx_automatic, timestep):
    """Test with discovery."""

    entity_id = "binary_sensor.kd101_smoke_detector_a10900_32"
    delay_off = 60

    await _signal_event(hass, EVENT_SMOKE_DETECTOR_PANIC)
    assert hass.states.get(entity_id).state == "on"

    # check for premature off
    await timestep(delay_off * 0.9)
    assert hass.states.get(entity_id).state == "on"

    # signal restart internal timer
    await _signal_event(hass, EVENT_SMOKE_DETECTOR_PANIC)

    # check for premature off
    await timestep(delay_off * 0.9)
    assert hass.states.get(entity_id).state == "on"

    # check for delayed off
    await timestep(delay_off * 0.2)
    assert hass.states.get(entity_id).state == "off"


async def test_motion(hass, rfxtrx_automatic):
    """Test motion entities."""

    entity_id = "binary_sensor.x10_security_motion_detector_a10900_32"

    await _signal_event(hass, EVENT_MOTION_DETECTOR_MOTION)
    assert hass.states.get(entity_id).state == "on"
    assert hass.states.get(entity_id).attributes.get("device_class") == "motion"

    await _signal_event(hass, EVENT_MOTION_DETECTOR_NO_MOTION)
    assert hass.states.get(entity_id).state == "off"


async def test_light(hass, rfxtrx_automatic):
    """Test light entities."""

    entity_id = "binary_sensor.x10_security_motion_detector_a10900_32"

    await _signal_event(hass, EVENT_LIGHT_DETECTOR_LIGHT)
    assert hass.states.get(entity_id).state == "on"

    await _signal_event(hass, EVENT_LIGHT_DETECTOR_DARK)
    assert hass.states.get(entity_id).state == "off"
