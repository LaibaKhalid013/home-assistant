"""Support for SimpliSafe locks."""
from simplipy.errors import SimplipyError
from simplipy.lock import LockStates
from simplipy.websocket import EVENT_LOCK_LOCKED, EVENT_LOCK_UNLOCKED

from homeassistant.components.lock import LockEntity
from homeassistant.core import callback

from . import SimpliSafeEntity
from .const import _LOGGER, DATA_CLIENT, DOMAIN

ATTR_LOCK_LOW_BATTERY = "lock_low_battery"
ATTR_JAMMED = "jammed"
ATTR_PIN_PAD_LOW_BATTERY = "pin_pad_low_battery"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up SimpliSafe locks based on a config entry."""
    simplisafe = hass.data[DOMAIN][DATA_CLIENT][entry.entry_id]
    async_add_entities(
        [
            SimpliSafeLock(simplisafe, system, lock)
            for system in simplisafe.systems.values()
            for lock in system.locks.values()
        ]
    )


class SimpliSafeLock(SimpliSafeEntity, LockEntity):
    """Define a SimpliSafe lock."""

    def __init__(self, simplisafe, system, lock):
        """Initialize."""
        super().__init__(simplisafe, system, lock.name, serial=lock.serial)
        self._is_locked = False
        self._lock = lock

        for event_type in (EVENT_LOCK_LOCKED, EVENT_LOCK_UNLOCKED):
            self.websocket_events_to_listen_for.append(event_type)

    @property
    def is_locked(self):
        """Return true if the lock is locked."""
        return self._is_locked

    async def async_lock(self, **kwargs):
        """Lock the lock."""
        try:
            await self._lock.lock()
        except SimplipyError as err:
            _LOGGER.error('Error while locking "%s": %s', self._lock.name, err)
            return

        self._is_locked = True

    async def async_unlock(self, **kwargs):
        """Unlock the lock."""
        try:
            await self._lock.unlock()
        except SimplipyError as err:
            _LOGGER.error('Error while unlocking "%s": %s', self._lock.name, err)
            return

        self._is_locked = False

    @callback
    def async_update_from_rest_api(self):
        """Update the entity with the provided REST API data."""
        self._attrs.update(
            {
                ATTR_LOCK_LOW_BATTERY: self._lock.lock_low_battery,
                ATTR_JAMMED: self._lock.state == LockStates.jammed,
                ATTR_PIN_PAD_LOW_BATTERY: self._lock.pin_pad_low_battery,
            }
        )

    @callback
    def async_update_from_websocket_event(self, event):
        """Update the entity with the provided websocket event data."""
        if event.event_type == EVENT_LOCK_LOCKED:
            self._is_locked = True
        else:
            self._is_locked = False
