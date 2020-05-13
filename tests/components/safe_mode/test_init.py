"""Tests for safe mode integration."""
from homeassistant.setup import async_setup_component


async def test_works(hass):
    """Test safe mode works."""
    assert await async_setup_component(hass, "safe_mode", {})
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids()) == 1
