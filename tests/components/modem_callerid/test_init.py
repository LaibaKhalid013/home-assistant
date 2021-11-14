"""Test Modem Caller ID integration."""
from phone_modem import exceptions

from homeassistant.components.modem_callerid.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant

from . import com_port, patch_init_modem

from tests.common import MockConfigEntry


async def test_setup_config(hass: HomeAssistant):
    """Test Modem Caller ID setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_hass(hass)
    with patch_init_modem():
        await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.LOADED


async def test_async_setup_entry_not_ready(hass: HomeAssistant):
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_hass(hass)

    with patch_init_modem() as modemmock:
        modemmock.side_effect = exceptions.SerialError
        await hass.config_entries.async_setup(entry.entry_id)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state == ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(DOMAIN)


async def test_unload_config_entry(hass: HomeAssistant):
    """Test unload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_hass(hass)
    with patch_init_modem():
        await hass.config_entries.async_setup(entry.entry_id)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(DOMAIN)
