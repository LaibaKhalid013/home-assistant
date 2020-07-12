"""Test Z-Wave Lights."""
from homeassistant.components.ozw.light import byte_to_zwave_brightness

from .common import setup_ozw


async def test_light(hass, light_data, light_msg, sent_messages):
    """Test setting up config entry."""
    receive_message = await setup_ozw(hass, fixture=light_data)

    # Test loaded
    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"

    # Test turning on
    # Beware that due to rounding, a roundtrip conversion does not always work
    new_brightness = 44
    new_transition = 0
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.led_bulb_6_multi_colour_level",
            "brightness": new_brightness,
            "transition": new_transition,
        },
        blocking=True,
    )
    assert len(sent_messages) == 2

    msg = sent_messages[0]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 0, "ValueIDKey": 1407375551070225}

    msg = sent_messages[1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {
        "Value": byte_to_zwave_brightness(new_brightness),
        "ValueIDKey": 659128337,
    }

    # Feedback on state
    light_msg.decode()
    light_msg.payload["Value"] = byte_to_zwave_brightness(new_brightness)
    light_msg.encode()
    receive_message(light_msg)
    await hass.async_block_till_done()

    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["brightness"] == new_brightness

    # Test turning off
    new_transition = 6553
    await hass.services.async_call(
        "light",
        "turn_off",
        {
            "entity_id": "light.led_bulb_6_multi_colour_level",
            "transition": new_transition,
        },
        blocking=True,
    )
    assert len(sent_messages) == 4

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 237, "ValueIDKey": 1407375551070225}

    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 0, "ValueIDKey": 659128337}

    # Feedback on state
    light_msg.decode()
    light_msg.payload["Value"] = 0
    light_msg.encode()
    receive_message(light_msg)
    await hass.async_block_till_done()

    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"

    # Test turn on without brightness
    new_transition = 127
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.led_bulb_6_multi_colour_level",
            "transition": new_transition,
        },
        blocking=True,
    )
    assert len(sent_messages) == 6

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 127, "ValueIDKey": 1407375551070225}

    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {
        "Value": 255,
        "ValueIDKey": 659128337,
    }

    # Feedback on state
    light_msg.decode()
    light_msg.payload["Value"] = byte_to_zwave_brightness(new_brightness)
    light_msg.encode()
    receive_message(light_msg)
    await hass.async_block_till_done()

    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["brightness"] == new_brightness

    # Test set brightness to 0
    new_brightness = 0
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.led_bulb_6_multi_colour_level",
            "brightness": new_brightness,
        },
        blocking=True,
    )
    assert len(sent_messages) == 7
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {
        "Value": byte_to_zwave_brightness(new_brightness),
        "ValueIDKey": 659128337,
    }

    # Feedback on state
    light_msg.decode()
    light_msg.payload["Value"] = byte_to_zwave_brightness(new_brightness)
    light_msg.encode()
    receive_message(light_msg)
    await hass.async_block_till_done()

    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"

    # Test setting color_name
    new_color = "blue"
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.led_bulb_6_multi_colour_level", "color_name": new_color},
        blocking=True,
    )
    assert len(sent_messages) == 9

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#0000ff0000", "ValueIDKey": 659341335}

    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    # Test setting hs_color
    new_color = [300, 70]
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.led_bulb_6_multi_colour_level", "hs_color": new_color},
        blocking=True,
    )
    assert len(sent_messages) == 11
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#ff4cff0000", "ValueIDKey": 659341335}

    # Test setting rgb_color
    new_color = [255, 154, 0]
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.led_bulb_6_multi_colour_level", "rgb_color": new_color},
        blocking=True,
    )
    assert len(sent_messages) == 13
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#ff99000000", "ValueIDKey": 659341335}

    # Test setting xy_color
    new_color = [0.52, 0.43]
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.led_bulb_6_multi_colour_level", "xy_color": new_color},
        blocking=True,
    )
    assert len(sent_messages) == 15
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#ffbb370000", "ValueIDKey": 659341335}

    # Test setting white_value
    new_color = 215
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": "light.led_bulb_6_multi_colour_level", "white_value": new_color},
        blocking=True,
    )
    assert len(sent_messages) == 17
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#000000d700", "ValueIDKey": 659341335}

    # Test setting rgb_color with white_value
    new_color = 215
    rgb_color = [192, 92, 35]
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.led_bulb_6_multi_colour_level",
            "white_value": new_color,
            "rgb_color": rgb_color,
        },
        blocking=True,
    )
    assert len(sent_messages) == 19
    msg = sent_messages[-1]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": 255, "ValueIDKey": 659128337}

    msg = sent_messages[-2]
    assert msg["topic"] == "OpenZWave/1/command/setvalue/"
    assert msg["payload"] == {"Value": "#ff7a2e0000", "ValueIDKey": 659341335}


async def test_no_rgb_light(hass, light_no_rgb_data, light_msg, sent_messages):
    """Test setting up config entry."""
    await setup_ozw(hass, fixture=light_no_rgb_data)

    # Test loaded no white level support
    state = hass.states.get("light.master_bedroom_l_level")
    assert state is not None
    assert state.state == "off"


async def test_no_ww_light(hass, light_no_ww_data, light_msg, sent_messages):
    """Test setting up config entry."""
    await setup_ozw(hass, fixture=light_no_ww_data)

    # Test loaded no ww support
    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"


async def test_no_cw_light(hass, light_no_cw_data, light_msg, sent_messages):
    """Test setting up config entry."""
    await setup_ozw(hass, fixture=light_no_cw_data)

    # Test loaded no cw support
    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"


async def test_wc_light(hass, light_wc_data, light_msg, sent_messages):
    """Test setting up config entry."""
    await setup_ozw(hass, fixture=light_wc_data)

    # Test loaded no white LED support
    state = hass.states.get("light.led_bulb_6_multi_colour_level")
    assert state is not None
    assert state.state == "off"
