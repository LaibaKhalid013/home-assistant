"""The Smart Meter Texas integration."""
import asyncio
import logging

from smart_meter_texas import Account, Client
from smart_meter_texas.exceptions import (
    SmartMeterTexasAPIError,
    SmartMeterTexasAuthError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    Debouncer,
    UpdateFailed,
)

from .const import DEBOUNCE_COOLDOWN, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Smart Meter Texas component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Smart Meter Texas from a config entry."""

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    account = Account(username, password)
    smartmetertexas = SmartMeterTexasData(hass, entry, account)
    try:
        await smartmetertexas.client.authenticate()
    except SmartMeterTexasAuthError:
        _LOGGER("Username or password was not accepted")
        return False
    except asyncio.TimeoutError:
        raise ConfigEntryNotReady

    await smartmetertexas.setup()

    async def async_update_data():
        await smartmetertexas.read_meters()
        return smartmetertexas

    # Use a DataUpdateCoordinator to manage the updates. This is due to the
    # Smart Meter Texas API which takes around 30 seconds to read a meter.
    # This avoids Home Assistant from complaining about the component taking
    # too long to update.
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Smart Meter Texas",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
        request_refresh_debouncer=Debouncer(
            hass, _LOGGER, cooldown=DEBOUNCE_COOLDOWN, immediate=True
        ),
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


class SmartMeterTexasData:
    """Manages coordinatation of API data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, account: Account):
        """Initialize the data coordintator."""
        self._entry = entry
        self.account = account
        websession = aiohttp_client.async_get_clientsession(hass)
        self.client = Client(websession, account)
        self.meters = []

    async def setup(self):
        """Fetch all of the user's meters."""
        try:
            self.meters = await self.account.fetch_meters(self.client)
        except SmartMeterTexasAuthError as error:
            _LOGGER.error("Error authenticating: %s", error)

        _LOGGER.debug("Discovered %s meter(s)", len(self.meters))

        if not self.meters:
            return False

        return True

    async def read_meters(self):
        """Read each meter."""
        for meter in self.meters:
            try:
                await meter.read_meter(self.client)
            except (SmartMeterTexasAPIError, SmartMeterTexasAuthError) as error:
                raise UpdateFailed(error)
        return self.meters


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
