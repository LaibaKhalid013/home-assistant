"""TemplateEntity utility class."""
from __future__ import annotations

from collections.abc import Callable
import contextlib
from dataclasses import dataclass
import itertools
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_FRIENDLY_NAME,
    CONF_ICON,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.core import CoreState, Event, State, callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    TrackTemplate,
    TrackTemplateResult,
    async_track_template_result,
)
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.helpers.template import Template, result_as_boolean

from . import convert_attribute_from_string, convert_attribute_to_string
from .const import (
    CONF_ATTRIBUTE_TEMPLATES,
    CONF_ATTRIBUTES,
    CONF_AVAILABILITY,
    CONF_AVAILABILITY_TEMPLATE,
    CONF_PICTURE,
    CONF_RESTORE,
)

_LOGGER = logging.getLogger(__name__)


TEMPLATE_ENTITY_AVAILABILITY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_AVAILABILITY): cv.template,
    }
)

TEMPLATE_ENTITY_ICON_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ICON): cv.template,
    }
)

TEMPLATE_ENTITY_RESTORE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_RESTORE): cv.boolean,
    }
)

TEMPLATE_ENTITY_COMMON_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ATTRIBUTES): vol.Schema({cv.string: cv.template}),
        vol.Optional(CONF_AVAILABILITY): cv.template,
        vol.Optional(CONF_ICON): cv.template,
        vol.Optional(CONF_PICTURE): cv.template,
        vol.Optional(CONF_RESTORE): cv.boolean,
    }
)

TEMPLATE_ENTITY_ATTRIBUTES_SCHEMA_LEGACY = vol.Schema(
    {
        vol.Optional(CONF_ATTRIBUTE_TEMPLATES, default={}): vol.Schema(
            {cv.string: cv.template}
        ),
    }
)

TEMPLATE_ENTITY_AVAILABILITY_SCHEMA_LEGACY = vol.Schema(
    {
        vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
    }
)

TEMPLATE_ENTITY_COMMON_SCHEMA_LEGACY = vol.Schema(
    {
        vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    }
).extend(TEMPLATE_ENTITY_AVAILABILITY_SCHEMA_LEGACY.schema)


LEGACY_FIELDS = {
    CONF_ICON_TEMPLATE: CONF_ICON,
    CONF_ENTITY_PICTURE_TEMPLATE: CONF_PICTURE,
    CONF_AVAILABILITY_TEMPLATE: CONF_AVAILABILITY,
    CONF_ATTRIBUTE_TEMPLATES: CONF_ATTRIBUTES,
    CONF_FRIENDLY_NAME: CONF_NAME,
}


def rewrite_common_legacy_to_modern_conf(
    entity_cfg: dict[str, Any], extra_legacy_fields: dict[str, str] = None
) -> dict[str, Any]:
    """Rewrite legacy config."""
    entity_cfg = {**entity_cfg}
    if extra_legacy_fields is None:
        extra_legacy_fields = {}

    for from_key, to_key in itertools.chain(
        LEGACY_FIELDS.items(), extra_legacy_fields.items()
    ):
        if from_key not in entity_cfg or to_key in entity_cfg:
            continue

        val = entity_cfg.pop(from_key)
        if isinstance(val, str):
            val = Template(val)
        entity_cfg[to_key] = val

    if CONF_NAME in entity_cfg and isinstance(entity_cfg[CONF_NAME], str):
        entity_cfg[CONF_NAME] = Template(entity_cfg[CONF_NAME])

    return entity_cfg


class _TemplateAttribute:
    """Attribute value linked to template result."""

    def __init__(
        self,
        entity: Entity,
        attribute: str,
        template: Template,
        validator: Callable[[Any], Any] = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool | None = False,
    ) -> None:
        """Template attribute."""
        self._entity = entity
        self._attribute = attribute
        self.template = template
        self.validator = validator
        self.on_update = on_update
        self.async_update = None
        self.none_on_template_error = none_on_template_error

    @property
    def attribute(self) -> str:
        """Return attribute."""
        return self._attribute

    @callback
    def async_setup(self):
        """Config update path for the attribute."""
        if self.on_update:
            return

        if not hasattr(self._entity, self._attribute):
            raise AttributeError(f"Attribute '{self._attribute}' does not exist.")

        self.on_update = self._default_update

    @callback
    def _default_update(self, result):
        attr_result = None if isinstance(result, TemplateError) else result
        setattr(self._entity, self._attribute, attr_result)

    @callback
    def handle_result(
        self,
        event: Event | None,
        template: Template,
        last_result: str | None | TemplateError,
        result: str | TemplateError,
    ) -> None:
        """Handle a template result event callback."""
        if isinstance(result, TemplateError):
            _LOGGER.error(
                "TemplateError('%s') "
                "while processing template '%s' "
                "for attribute '%s' in entity '%s'",
                result,
                self.template,
                self._attribute,
                self._entity.entity_id,
            )
            if self.none_on_template_error:
                self._default_update(result)
            else:
                assert self.on_update
                self.on_update(result)
            return

        if not self.validator:
            assert self.on_update
            self.on_update(result)
            return

        try:
            validated = self.validator(result)
        except vol.Invalid as ex:
            _LOGGER.error(
                "Error validating template result '%s' "
                "from template '%s' "
                "for attribute '%s' in entity %s "
                "validation message '%s'",
                result,
                self.template,
                self._attribute,
                self._entity.entity_id,
                ex.msg,
            )
            assert self.on_update
            self.on_update(None)
            return

        assert self.on_update
        self.on_update(validated)
        return


class TemplateEntity(Entity):
    """Entity that uses templates to calculate attributes."""

    _attr_available = True
    _attr_entity_picture = None
    _attr_icon = None
    _attr_should_poll = False

    def __init__(
        self,
        hass,
        *,
        availability_template=None,
        icon_template=None,
        entity_picture_template=None,
        attribute_templates=None,
        config=None,
        fallback_name=None,
        unique_id=None,
    ):
        """Template Entity."""
        self._template_attrs = {}
        self._async_update = None
        self._attr_extra_state_attributes = {}
        self._self_ref_update_count = 0
        self._attr_unique_id = unique_id
        if config is None:
            self._attribute_templates = attribute_templates
            self._availability_template = availability_template
            self._icon_template = icon_template
            self._entity_picture_template = entity_picture_template
            self._friendly_name_template = None
            self._restore = False
        else:
            self._attribute_templates = config.get(CONF_ATTRIBUTES)
            self._availability_template = config.get(CONF_AVAILABILITY)
            self._icon_template = config.get(CONF_ICON)
            self._entity_picture_template = config.get(CONF_PICTURE)
            self._friendly_name_template = config.get(CONF_NAME)
            self._restore = config.get(CONF_RESTORE)

        # Try to render the name as it can influence the entity ID
        self._attr_name = fallback_name
        if self._friendly_name_template:
            self._friendly_name_template.hass = hass
            with contextlib.suppress(TemplateError):
                self._attr_name = self._friendly_name_template.async_render(
                    parse_result=False
                )

        # Templates will not render while the entity is unavailable, try to render the
        # icon and picture templates.
        if self._entity_picture_template:
            self._entity_picture_template.hass = hass
            with contextlib.suppress(TemplateError):
                self._attr_entity_picture = self._entity_picture_template.async_render(
                    parse_result=False
                )

        if self._icon_template:
            self._icon_template.hass = hass
            with contextlib.suppress(TemplateError):
                self._attr_icon = self._icon_template.async_render(parse_result=False)

    @callback
    def _update_available(self, result):
        if isinstance(result, TemplateError):
            self._attr_available = True
            return

        self._attr_available = result_as_boolean(result)

    @callback
    def _update_state(self, result):
        if self._availability_template:
            return

        self._attr_available = not isinstance(result, TemplateError)

    @callback
    def _add_attribute_template(self, attribute_key, attribute_template):
        """Create a template tracker for the attribute."""

        def _update_attribute(result):
            attr_result = None if isinstance(result, TemplateError) else result
            self._attr_extra_state_attributes[attribute_key] = attr_result

        self.add_template_attribute(
            attribute_key, attribute_template, None, _update_attribute
        )

    def add_template_attribute(
        self,
        attribute: str,
        template: Template,
        validator: Callable[[Any], Any] = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool = False,
    ) -> None:
        """
        Call in the constructor to add a template linked to a attribute.

        Parameters
        ----------
        attribute
            The name of the attribute to link to. This attribute must exist
            unless a custom on_update method is supplied.
        template
            The template to calculate.
        validator
            Validator function to parse the result and ensure it's valid.
        on_update
            Called to store the template result rather than storing it
            the supplied attribute. Passed the result of the validator, or None
            if the template or validator resulted in an error.

        """
        assert self.hass is not None, "hass cannot be None"
        template.hass = self.hass
        template_attribute = _TemplateAttribute(
            self, attribute, template, validator, on_update, none_on_template_error
        )
        self._template_attrs.setdefault(template, [])
        self._template_attrs[template].append(template_attribute)

    @callback
    def _handle_results(
        self,
        event: Event | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        """Call back the results to the attributes."""
        if event:
            self.async_set_context(event.context)

        entity_id = event and event.data.get(ATTR_ENTITY_ID)

        if entity_id and entity_id == self.entity_id:
            self._self_ref_update_count += 1
        else:
            self._self_ref_update_count = 0

        if self._self_ref_update_count > len(self._template_attrs):
            for update in updates:
                _LOGGER.warning(
                    "Template loop detected while processing event: %s, skipping template render for Template[%s]",
                    event,
                    update.template.template,
                )
            return

        for update in updates:
            for attr in self._template_attrs[update.template]:
                attr.handle_result(
                    event, update.template, update.last_result, update.result
                )

        self.async_write_ha_state()

    async def _async_template_startup(self, *_) -> None:
        template_var_tups: list[TrackTemplate] = []
        has_availability_template = False
        for template, attributes in self._template_attrs.items():
            template_var_tup = TrackTemplate(template, None)
            is_availability_template = False
            for attribute in attributes:
                # pylint: disable-next=protected-access
                if attribute._attribute == "_attr_available":
                    has_availability_template = True
                    is_availability_template = True
                attribute.async_setup()
            # Insert the availability template first in the list
            if is_availability_template:
                template_var_tups.insert(0, template_var_tup)
            else:
                template_var_tups.append(template_var_tup)

        result_info = async_track_template_result(
            self.hass,
            template_var_tups,
            self._handle_results,
            has_super_template=has_availability_template,
        )
        self.async_on_remove(result_info.async_remove)
        self._async_update = result_info.async_refresh
        result_info.async_refresh()

    def _add_all_template_attributes(self) -> None:
        """Add the additional template attributes."""
        if self._availability_template is not None:
            self.add_template_attribute(
                "_attr_available",
                self._availability_template,
                None,
                self._update_available,
            )
        if self._attribute_templates is not None:
            for key, value in self._attribute_templates.items():
                self._add_attribute_template(key, value)
        if self._icon_template is not None:
            self.add_template_attribute(
                "_attr_icon", self._icon_template, vol.Or(cv.whitespace, cv.icon)
            )
        if self._entity_picture_template is not None:
            self.add_template_attribute(
                "_attr_entity_picture", self._entity_picture_template
            )
        if (
            self._friendly_name_template is not None
            and not self._friendly_name_template.is_static
        ):
            self.add_template_attribute("_attr_name", self._friendly_name_template)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""

        self._add_all_template_attributes()

        if self.hass.state == CoreState.running:
            await self._async_template_startup()
            return

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, self._async_template_startup
        )

    async def async_update(self) -> None:
        """Call for forced update."""
        self._async_update()


class TemplateRestoreEntity(RestoreEntity, TemplateEntity):
    """Template Entity that restores data."""

    async def restore_entity(
        self,
    ) -> tuple[State | None, dict[Template, Any] | None]:
        """Restore the entity."""

        if not self._restore:
            return None, None

        if (last_sensor_state := await self.async_get_last_state()) is None:
            _LOGGER.debug("No state found to restore for entity %s", self.entity_id)
            return None, None

        # Restore all attributes.
        _LOGGER.debug("Restoring entity %s", self.entity_id)

        # Restore any attributes.
        if self._attribute_templates is not None:
            for key in self._attribute_templates:
                try:
                    self._attr_extra_state_attributes.update(
                        {key: last_sensor_state.attributes[key]}
                    )
                    _LOGGER.debug(
                        "Restored attribute %s for entity %s", key, self.entity_id
                    )
                except KeyError:
                    pass

        # Restore extra data
        if (last_sensor_data := await self.async_get_last_template_data()) is None:
            _LOGGER.debug(
                "No extra data found to restore for entity %s", self.entity_id
            )
            return last_sensor_state, None

        for template, attributes in self._template_attrs.items():
            try:
                template_attr = last_sensor_data[template]
            except KeyError:
                _LOGGER.debug(
                    "Unable to find template key %s for entity %s",
                    template,
                    self.entity_id,
                )
                continue

            for attribute in attributes:
                try:
                    value = template_attr[attribute.attribute]
                except KeyError:
                    _LOGGER.debug(
                        "Unable to find attribute %s for template key %s for entity %s",
                        attribute.attribute,
                        template,
                        self.entity_id,
                    )
                    continue

                if attribute.on_update is None:
                    try:
                        setattr(self, attribute.attribute, value)
                    except AttributeError:
                        _LOGGER.debug(
                            "Attribute %s does not exist in entity %s, unable to restore",
                            attribute.attribute,
                            self.entity_id,
                        )
                        continue
                else:
                    attribute.on_update(value)

                _LOGGER.debug(
                    "Attribute %s restored to value %s for entity %s",
                    attribute.attribute,
                    value,
                    self.entity_id,
                )

        return (last_sensor_state, last_sensor_data)

    @property
    def extra_restore_state_data(self) -> TemplateExtraStoredData | None:
        """Return sensor specific state data to be restored."""
        return (
            TemplateExtraStoredData(self, self._template_attrs)
            if self._restore
            else TemplateExtraStoredData(self, {})
        )

    async def async_get_last_template_data(self) -> dict[Template, Any] | None:
        """Restore native_value and native_unit_of_measurement."""
        if not self._restore:
            return None

        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return TemplateExtraStoredData(self, self._template_attrs).from_dict(
            restored_last_extra_data.as_dict()
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""

        self._add_all_template_attributes()

        await self.restore_entity()

        if self.hass.state == CoreState.running:
            await self._async_template_startup()
            return

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, self._async_template_startup
        )


@dataclass
class TemplateExtraStoredData(ExtraStoredData):
    """Object to hold extra stored data."""

    template_entity: TemplateEntity
    template_attrs: dict[Template, list[_TemplateAttribute]]

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the sensor data."""
        template_values: dict[str, Any] = {}
        for template, attributes in self.template_attrs.items():
            for attribute in attributes:
                try:
                    value = convert_attribute_to_string(
                        getattr(self.template_entity, attribute.attribute)
                    )
                except AttributeError:
                    continue

                _LOGGER.debug(
                    "Storing attribute %s for template %s with value %s",
                    attribute.attribute,
                    template,
                    value,
                )
                template_values.update({attribute.attribute: value})

        return template_values

    def from_dict(self, restored: dict[str, Any]) -> dict[Template, dict[str, Any]]:
        """Initialize a stored sensor state from a dict."""
        template_values: dict[Template, Any] = {}
        for template, attributes in self.template_attrs.items():
            for attribute in attributes:
                try:
                    value = convert_attribute_from_string(restored[attribute.attribute])
                except KeyError:
                    continue

                _LOGGER.debug(
                    "Retrieved attribute %s for template %s with value %s",
                    attribute.attribute,
                    template,
                    value,
                )
                template_values.setdefault(template, {})
                template_values[template].update({attribute.attribute: value})
        return template_values
