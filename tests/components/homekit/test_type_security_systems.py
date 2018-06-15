"""Test different accessory types: Security Systems."""
import pytest

from homeassistant.components.homekit.type_security_systems import \
    SecuritySystem
from homeassistant.const import ATTR_CODE, ATTR_ENTITY_ID

from tests.common import async_mock_service


async def test_switch_set_state(hass, hk_driver):
    """Test if accessory and HA are updated accordingly."""
    code = '1234'
    config = {ATTR_CODE: code}
    entity_id = 'alarm_control_panel.test'

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = SecuritySystem(hass, hk_driver, 'Security System',
                         entity_id, 2, config)
    await hass.async_add_job(acc.run)

    assert acc.aid == 2
    assert acc.category == 11  # AlarmSystem

    assert acc.char_current_state.value == 3
    assert acc.char_target_state.value == 3

    hass.states.async_set(entity_id, 'armed_away')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 1
    assert acc.char_current_state.value == 1

    hass.states.async_set(entity_id, 'armed_home')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 0
    assert acc.char_current_state.value == 0

    hass.states.async_set(entity_id, 'armed_night')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 2
    assert acc.char_current_state.value == 2

    hass.states.async_set(entity_id, 'disarmed')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 3
    assert acc.char_current_state.value == 3

    hass.states.async_set(entity_id, 'triggered')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 3
    assert acc.char_current_state.value == 4

    hass.states.async_set(entity_id, 'unknown')
    await hass.async_block_till_done()
    assert acc.char_target_state.value == 3
    assert acc.char_current_state.value == 4

    # Set from HomeKit
    call_arm_home = async_mock_service(hass, 'alarm_control_panel',
                                       'alarm_arm_home')
    call_arm_away = async_mock_service(hass, 'alarm_control_panel',
                                       'alarm_arm_away')
    call_arm_night = async_mock_service(hass, 'alarm_control_panel',
                                        'alarm_arm_night')
    call_disarm = async_mock_service(hass, 'alarm_control_panel',
                                     'alarm_disarm')

    await hass.async_add_job(acc.char_target_state.client_update_value, 0)
    await hass.async_block_till_done()
    assert call_arm_home
    assert call_arm_home[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_arm_home[0].data[ATTR_CODE] == code
    assert acc.char_target_state.value == 0

    await hass.async_add_job(acc.char_target_state.client_update_value, 1)
    await hass.async_block_till_done()
    assert call_arm_away
    assert call_arm_away[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_arm_away[0].data[ATTR_CODE] == code
    assert acc.char_target_state.value == 1

    await hass.async_add_job(acc.char_target_state.client_update_value, 2)
    await hass.async_block_till_done()
    assert call_arm_night
    assert call_arm_night[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_arm_night[0].data[ATTR_CODE] == code
    assert acc.char_target_state.value == 2

    await hass.async_add_job(acc.char_target_state.client_update_value, 3)
    await hass.async_block_till_done()
    assert call_disarm
    assert call_disarm[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_disarm[0].data[ATTR_CODE] == code
    assert acc.char_target_state.value == 3


@pytest.mark.parametrize('config', [{}, {ATTR_CODE: None}])
async def test_no_alarm_code(hass, hk_driver, config):
    """Test accessory if security_system doesn't require an alarm_code."""
    entity_id = 'alarm_control_panel.test'

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = SecuritySystem(hass, hk_driver, 'Security System',
                         entity_id, 2, config)

    # Set from HomeKit
    call_arm_home = async_mock_service(hass, 'alarm_control_panel',
                                       'alarm_arm_home')

    await hass.async_add_job(acc.char_target_state.client_update_value, 0)
    await hass.async_block_till_done()
    assert call_arm_home
    assert call_arm_home[0].data[ATTR_ENTITY_ID] == entity_id
    assert ATTR_CODE not in call_arm_home[0].data
    assert acc.char_target_state.value == 0
