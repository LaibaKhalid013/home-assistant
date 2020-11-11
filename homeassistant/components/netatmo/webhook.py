"""The Netatmo integration."""
import logging

from homeassistant.const import ATTR_ID, ATTR_DEVICE_ID
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_EVENT_TYPE,
    ATTR_FACE_URL,
    ATTR_IS_KNOWN,
    ATTR_NAME,
    ATTR_PERSONS,
    DATA_DEVICE_IDS,
    DATA_PERSONS,
    DEFAULT_PERSON,
    DOMAIN,
    EVENT_ID_MAP,
    NETATMO_EVENT,
)

_LOGGER = logging.getLogger(__name__)

EVENT_TYPE_MAP = {
    "outdoor": "",
    "therm_mode": "",
}


async def handle_webhook(hass, webhook_id, request):
    """Handle webhook callback."""
    try:
        data = await request.json()
    except ValueError as err:
        _LOGGER.error("Error in data: %s", err)
        return None

    _LOGGER.debug("Got webhook data: %s", data)

    event_type = data.get(ATTR_EVENT_TYPE)

    if event_type in EVENT_TYPE_MAP:
        await async_send_event(hass, event_type, data)

        for event_data in data.get(EVENT_TYPE_MAP[event_type], []):
            await async_evaluate_event(hass, event_data)

    else:
        await async_evaluate_event(hass, data)


@callback
async def async_evaluate_event(hass, event_data):
    """Evaluate events from webhook."""
    event_type = event_data.get(ATTR_EVENT_TYPE)

    if event_type == "person":
        for person in event_data.get(ATTR_PERSONS):
            person_event_data = dict(event_data)
            person_event_data[ATTR_ID] = person.get(ATTR_ID)
            person_event_data[ATTR_NAME] = hass.data[DOMAIN][DATA_PERSONS].get(
                person_event_data[ATTR_ID], DEFAULT_PERSON
            )
            person_event_data[ATTR_IS_KNOWN] = person.get(ATTR_IS_KNOWN)
            person_event_data[ATTR_FACE_URL] = person.get(ATTR_FACE_URL)

            _LOGGER.debug("%s: %s", event_type, person_event_data)
            await async_send_event(hass, event_type, person_event_data)

    else:
        _LOGGER.debug("%s: %s", event_type, event_data)
        await async_send_event(hass, event_type, event_data)


@callback
async def async_send_event(hass, event_type, data):
    """Send events."""
    async_dispatcher_send(
        hass,
        f"signal-{DOMAIN}-webhook-{event_type}",
        {"type": event_type, "data": data},
    )

    if event_type not in EVENT_ID_MAP:
        return

    hass.bus.async_fire(
        event_type=NETATMO_EVENT,
        event_data={
            "type": event_type,
            "data": data,
            ATTR_DEVICE_ID: hass.data[DOMAIN][DATA_DEVICE_IDS].get(
                data.get(EVENT_ID_MAP.get(event_type))
            ),
        },
    )
