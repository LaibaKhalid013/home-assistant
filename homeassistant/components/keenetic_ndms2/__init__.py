"""The keenetic_ndms2 component."""

from homeassistant.components import binary_sensor, device_tracker
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant

from .const import DOMAIN, ROUTER, UNDO_UPDATE_LISTENER
from .router import KeeneticRouter

PLATFORMS = [device_tracker.DOMAIN, binary_sensor.DOMAIN]


async def async_setup(hass: HomeAssistant, _config: Config) -> bool:
    """Set up configured entries."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the component."""

    router = KeeneticRouter(hass, config_entry)
    await router.async_setup()

    undo_listener = config_entry.add_update_listener(update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        ROUTER: router,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN][config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    for component in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(config_entry, component)

    router: KeeneticRouter = hass.data[DOMAIN][config_entry.entry_id][ROUTER]

    await router.async_teardown()

    hass.data[DOMAIN].pop(config_entry.entry_id)

    return True


async def update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
