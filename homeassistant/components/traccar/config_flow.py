"""Config flow for Traccar."""
from homeassistant.helpers import config_entry_flow
from .const import DOMAIN


config_entry_flow.register_webhook_flow(
    DOMAIN,
    'Traccar / Osmand Webhook',
    {
        'docs_url': 'https://www.home-assistant.io/components/traccar/'
    }
)
