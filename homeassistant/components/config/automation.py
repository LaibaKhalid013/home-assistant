"""Provide configuration end points for Automations."""
import uuid

from homeassistant.components.automation.config import (
    DOMAIN,
    PLATFORM_SCHEMA,
    async_validate_config_item,
)
from homeassistant.config import AUTOMATION_CONFIG_PATH
from homeassistant.const import CONF_ID, SERVICE_RELOAD
from homeassistant.helpers import config_validation as cv, entity_registry

from . import ACTION_DELETE, EditIdBasedConfigView


async def async_setup(hass):
    """Set up the Automation config API."""

    async def hook(action, config_key):
        """post_write_hook for Config View that reloads automations."""
        await hass.services.async_call(DOMAIN, SERVICE_RELOAD)

        if action != ACTION_DELETE:
            return

        ent_reg = await entity_registry.async_get_registry(hass)

        entity_id = ent_reg.async_get_entity_id(DOMAIN, DOMAIN, config_key)

        if entity_id is None:
            return

        ent_reg.async_remove(entity_id)

    hass.http.register_view(
        EditAutomationConfigView(
            DOMAIN,
            "config",
            AUTOMATION_CONFIG_PATH,
            cv.string,
            PLATFORM_SCHEMA,
            post_write_hook=hook,
            data_validator=async_validate_config_item,
        )
    )
    return True


class EditAutomationConfigView(EditIdBasedConfigView):
    """Edit automation config."""

    def _write_value(self, hass, data, config_key, new_value):
        """Set value."""
        updated_value = {CONF_ID: config_key}

        for key in ("id", "alias", "description", "trigger", "condition", "action"):
            if key in new_value:
                updated_value[key] = new_value[key]

        updated_value.update(new_value)

        updated = False
        for index, cur_value in enumerate(data):
            # When people copy paste their automations to the config file,
            # they sometimes forget to add IDs. Fix it here.
            if CONF_ID not in cur_value:
                cur_value[CONF_ID] = uuid.uuid4().hex

            elif cur_value[CONF_ID] == config_key:
                data[index] = updated_value
                updated = True

        if not updated:
            data.append(updated_value)
