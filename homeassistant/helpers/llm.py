"""Module to coordinate llm tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import voluptuous as vol
from voluptuous_openapi import UNSUPPORTED, convert

from homeassistant.components.climate.intent import INTENT_GET_TEMPERATURE
from homeassistant.components.conversation.trace import (
    ConversationTraceEventType,
    async_conversation_trace_append,
)
from homeassistant.components.cover.intent import INTENT_CLOSE_COVER, INTENT_OPEN_COVER
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.components.intent import async_device_supports_timers
from homeassistant.components.script import ATTR_VARIABLES, DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.weather.intent import INTENT_GET_WEATHER
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.core import Context, HomeAssistant, State, callback, split_entity_id
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import yaml
from homeassistant.util.json import JsonObjectType

from . import (
    area_registry as ar,
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    intent,
    selector,
    service,
)
from .singleton import singleton

LLM_API_ASSIST = "assist"

BASE_PROMPT = (
    'Current time is {{ now().strftime("%H:%M:%S") }}. '
    'Today\'s date is {{ now().strftime("%Y-%m-%d") }}.\n'
)

DEFAULT_INSTRUCTIONS_PROMPT = """You are a voice assistant for Home Assistant.
Answer in plain text. Keep it simple and to the point.
"""


@callback
def async_render_no_api_prompt(hass: HomeAssistant) -> str:
    """Return the prompt to be used when no API is configured."""
    return (
        "Only if the user wants to control a device, tell them to edit the AI configuration "
        "and allow access to Home Assistant."
    )


@singleton("llm")
@callback
def _async_get_apis(hass: HomeAssistant) -> dict[str, API]:
    """Get all the LLM APIs."""
    return {
        LLM_API_ASSIST: AssistAPI(hass=hass),
    }


@callback
def async_register_api(hass: HomeAssistant, api: API) -> None:
    """Register an API to be exposed to LLMs."""
    apis = _async_get_apis(hass)

    if api.id in apis:
        raise HomeAssistantError(f"API {api.id} is already registered")

    apis[api.id] = api


async def async_get_api(
    hass: HomeAssistant, api_id: str, llm_context: LLMContext
) -> APIInstance:
    """Get an API."""
    apis = _async_get_apis(hass)

    if api_id not in apis:
        raise HomeAssistantError(f"API {api_id} not found")

    return await apis[api_id].async_get_api_instance(llm_context)


@callback
def async_get_apis(hass: HomeAssistant) -> list[API]:
    """Get all the LLM APIs."""
    return list(_async_get_apis(hass).values())


@dataclass(slots=True)
class LLMContext:
    """Tool input to be processed."""

    platform: str
    context: Context | None
    user_prompt: str | None
    language: str | None
    assistant: str | None
    device_id: str | None


@dataclass(slots=True)
class ToolInput:
    """Tool input to be processed."""

    tool_name: str
    tool_args: dict[str, Any]


class Tool:
    """LLM Tool base class."""

    name: str
    description: str | None = None
    parameters: vol.Schema = vol.Schema({})

    @abstractmethod
    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Call the tool."""
        raise NotImplementedError

    def __repr__(self) -> str:
        """Represent a string of a Tool."""
        return f"<{self.__class__.__name__} - {self.name}>"


@dataclass
class APIInstance:
    """Instance of an API to be used by an LLM."""

    api: API
    api_prompt: str
    llm_context: LLMContext
    tools: list[Tool]

    async def async_call_tool(self, tool_input: ToolInput) -> JsonObjectType:
        """Call a LLM tool, validate args and return the response."""
        async_conversation_trace_append(
            ConversationTraceEventType.LLM_TOOL_CALL,
            {"tool_name": tool_input.tool_name, "tool_args": tool_input.tool_args},
        )

        for tool in self.tools:
            if tool.name == tool_input.tool_name:
                break
        else:
            raise HomeAssistantError(f'Tool "{tool_input.tool_name}" not found')

        return await tool.async_call(self.api.hass, tool_input, self.llm_context)


@dataclass(slots=True, kw_only=True)
class API(ABC):
    """An API to expose to LLMs."""

    hass: HomeAssistant
    id: str
    name: str

    @abstractmethod
    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return the instance of the API."""
        raise NotImplementedError


class IntentTool(Tool):
    """LLM Tool representing an Intent."""

    def __init__(
        self,
        intent_handler: intent.IntentHandler,
    ) -> None:
        """Init the class."""
        self.name = intent_handler.intent_type
        self.description = (
            intent_handler.description or f"Execute Home Assistant {self.name} intent"
        )
        self.extra_slots = None
        if not (slot_schema := intent_handler.slot_schema):
            return

        slot_schema = {**slot_schema}
        extra_slots = set()

        for field in ("preferred_area_id", "preferred_floor_id"):
            if field in slot_schema:
                extra_slots.add(field)
                del slot_schema[field]

        self.parameters = vol.Schema(slot_schema)
        if extra_slots:
            self.extra_slots = extra_slots

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Handle the intent."""
        slots = {key: {"value": val} for key, val in tool_input.tool_args.items()}

        if self.extra_slots and llm_context.device_id:
            device_reg = dr.async_get(hass)
            device = device_reg.async_get(llm_context.device_id)

            area: ar.AreaEntry | None = None
            floor: fr.FloorEntry | None = None
            if device:
                area_reg = ar.async_get(hass)
                if device.area_id and (area := area_reg.async_get_area(device.area_id)):
                    if area.floor_id:
                        floor_reg = fr.async_get(hass)
                        floor = floor_reg.async_get_floor(area.floor_id)

            for slot_name, slot_value in (
                ("preferred_area_id", area.id if area else None),
                ("preferred_floor_id", floor.floor_id if floor else None),
            ):
                if slot_value and slot_name in self.extra_slots:
                    slots[slot_name] = {"value": slot_value}

        intent_response = await intent.async_handle(
            hass=hass,
            platform=llm_context.platform,
            intent_type=self.name,
            slots=slots,
            text_input=llm_context.user_prompt,
            context=llm_context.context,
            language=llm_context.language,
            assistant=llm_context.assistant,
            device_id=llm_context.device_id,
        )
        response = intent_response.as_dict()
        del response["language"]
        del response["card"]
        return response


class AssistAPI(API):
    """API exposing Assist API to LLMs."""

    IGNORE_INTENTS = {
        INTENT_GET_TEMPERATURE,
        INTENT_GET_WEATHER,
        INTENT_OPEN_COVER,  # deprecated
        INTENT_CLOSE_COVER,  # deprecated
        intent.INTENT_GET_STATE,
        intent.INTENT_NEVERMIND,
        intent.INTENT_TOGGLE,
    }

    def __init__(self, hass: HomeAssistant) -> None:
        """Init the class."""
        super().__init__(
            hass=hass,
            id=LLM_API_ASSIST,
            name="Assist",
        )

    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return the instance of the API."""
        if llm_context.assistant:
            exposed_entities: dict | None = _get_exposed_entities(
                self.hass, llm_context.assistant
            )
        else:
            exposed_entities = None

        return APIInstance(
            api=self,
            api_prompt=self._async_get_api_prompt(llm_context, exposed_entities),
            llm_context=llm_context,
            tools=self._async_get_tools(llm_context, exposed_entities),
        )

    @callback
    def _async_get_api_prompt(
        self, llm_context: LLMContext, exposed_entities: dict | None
    ) -> str:
        """Return the prompt for the API."""
        if not exposed_entities:
            return (
                "Only if the user wants to control a device, tell them to expose entities "
                "to their voice assistant in Home Assistant."
            )

        prompt = [
            (
                "When controlling Home Assistant always call the intent tools. "
                "Use HassTurnOn to lock and HassTurnOff to unlock a lock. "
                "When controlling a device, prefer passing just its name and its domain "
                "(what comes before the dot in its entity id). "
                "When controlling an area, prefer passing just area name and domain."
            )
        ]
        area: ar.AreaEntry | None = None
        floor: fr.FloorEntry | None = None
        if llm_context.device_id:
            device_reg = dr.async_get(self.hass)
            device = device_reg.async_get(llm_context.device_id)

            if device:
                area_reg = ar.async_get(self.hass)
                if device.area_id and (area := area_reg.async_get_area(device.area_id)):
                    floor_reg = fr.async_get(self.hass)
                    if area.floor_id:
                        floor = floor_reg.async_get_floor(area.floor_id)

            extra = "and all generic commands like 'turn on the lights' should target this area."

        if floor and area:
            prompt.append(f"You are in area {area.name} (floor {floor.name}) {extra}")
        elif area:
            prompt.append(f"You are in area {area.name} {extra}")
        else:
            prompt.append(
                "When a user asks to turn on all devices of a specific type, "
                "ask user to specify an area, unless there is only one device of that type."
            )

        if not llm_context.device_id or not async_device_supports_timers(
            self.hass, llm_context.device_id
        ):
            prompt.append("This device does not support timers.")

        if exposed_entities:
            prompt.append(
                "An overview of the areas and the devices in this smart home:"
            )
            prompt.append(yaml.dump(exposed_entities))

        return "\n".join(prompt)

    @callback
    def _async_get_tools(
        self, llm_context: LLMContext, exposed_entities: dict | None
    ) -> list[Tool]:
        """Return a list of LLM tools."""
        ignore_intents = self.IGNORE_INTENTS
        if not llm_context.device_id or not async_device_supports_timers(
            self.hass, llm_context.device_id
        ):
            ignore_intents = ignore_intents | {
                intent.INTENT_START_TIMER,
                intent.INTENT_CANCEL_TIMER,
                intent.INTENT_INCREASE_TIMER,
                intent.INTENT_DECREASE_TIMER,
                intent.INTENT_PAUSE_TIMER,
                intent.INTENT_UNPAUSE_TIMER,
                intent.INTENT_TIMER_STATUS,
            }

        intent_handlers = [
            intent_handler
            for intent_handler in intent.async_get(self.hass)
            if intent_handler.intent_type not in ignore_intents
        ]

        exposed_domains: set[str] | None = None
        if exposed_entities is not None:
            exposed_domains = {
                split_entity_id(entity_id)[0] for entity_id in exposed_entities
            }
            intent_handlers = [
                intent_handler
                for intent_handler in intent_handlers
                if intent_handler.platforms is None
                or intent_handler.platforms & exposed_domains
            ]

        tools: list[Tool] = [
            IntentTool(intent_handler) for intent_handler in intent_handlers
        ]

        if llm_context.assistant is not None:
            for state in self.hass.states.async_all(SCRIPT_DOMAIN):
                if not async_should_expose(
                    self.hass, llm_context.assistant, state.entity_id
                ):
                    continue

                tools.append(ScriptTool(self.hass, state))

        return tools


def _get_exposed_entities(
    hass: HomeAssistant, assistant: str
) -> dict[str, dict[str, Any]]:
    """Get exposed entities."""
    area_registry = ar.async_get(hass)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    interesting_attributes = {
        "temperature",
        "current_temperature",
        "temperature_unit",
        "brightness",
        "humidity",
        "unit_of_measurement",
        "device_class",
        "current_position",
        "percentage",
        "volume_level",
        "media_title",
        "media_artist",
        "media_album_name",
    }

    entities = {}

    for state in hass.states.async_all():
        if state.domain == SCRIPT_DOMAIN:
            continue

        if not async_should_expose(hass, assistant, state.entity_id):
            continue

        entity_entry = entity_registry.async_get(state.entity_id)
        names = [state.name]
        area_names = []

        if entity_entry is not None:
            names.extend(entity_entry.aliases)
            if entity_entry.area_id and (
                area := area_registry.async_get_area(entity_entry.area_id)
            ):
                # Entity is in area
                area_names.append(area.name)
                area_names.extend(area.aliases)
            elif entity_entry.device_id and (
                device := device_registry.async_get(entity_entry.device_id)
            ):
                # Check device area
                if device.area_id and (
                    area := area_registry.async_get_area(device.area_id)
                ):
                    area_names.append(area.name)
                    area_names.extend(area.aliases)

        info: dict[str, Any] = {
            "names": ", ".join(names),
            "state": state.state,
        }

        if area_names:
            info["areas"] = ", ".join(area_names)

        if attributes := {
            attr_name: str(attr_value) if isinstance(attr_value, Enum) else attr_value
            for attr_name, attr_value in state.attributes.items()
            if attr_name in interesting_attributes
        }:
            info["attributes"] = attributes

        entities[state.entity_id] = info

    return entities


def selector_serializer(schema: Any) -> Any:  # noqa: C901
    """Convert selectors into OpenAPI schema."""
    if not isinstance(schema, selector.Selector):
        return UNSUPPORTED

    if isinstance(schema, selector.BackupLocationSelector):
        return {"type": "string", "pattern": "^(?:\\/backup|\\w+)$"}

    if isinstance(schema, selector.BooleanSelector):
        return {"type": "boolean"}

    if isinstance(schema, selector.ColorRGBSelector):
        return {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3,
            "format": "RGB",
        }

    if isinstance(schema, selector.ConditionSelector):
        return convert(cv.CONDITIONS_SCHEMA)

    if isinstance(schema, selector.ConstantSelector):
        return {"enum": [schema.config["value"]]}

    if isinstance(schema, (selector.NumberSelector, selector.ColorTempSelector)):
        result: dict[str, Any] = {"type": "number"}
        if "min" in schema.config or "min_mireds" in schema.config:
            result["minimum"] = schema.config.get("min") or schema.config.get(
                "min_mireds"
            )
        if "max" in schema.config or "max_mireds" in schema.config:
            result["maximum"] = schema.config.get("max") or schema.config.get(
                "max_mireds"
            )
        return result

    if isinstance(schema, selector.CountrySelector):
        if schema.config.get("countries"):
            return {"type": "string", "enum": schema.config["countries"]}
        return {"type": "string", "format": "ISO 3166-1 alpha-2"}

    if isinstance(schema, selector.DateSelector):
        return {"type": "string", "format": "date"}

    if isinstance(schema, selector.DateTimeSelector):
        return {"type": "string", "format": "date-time"}

    if isinstance(schema, selector.DurationSelector):
        return convert(cv.time_period_dict)

    if isinstance(schema, selector.LanguageSelector):
        if schema.config.get("languages"):
            return {"type": "string", "enum": schema.config["languages"]}
        return {"type": "string", "format": "RFC 5646"}

    if isinstance(schema, (selector.LocationSelector, selector.MediaSelector)):
        return convert(schema.DATA_SCHEMA)

    if isinstance(schema, selector.ObjectSelector):
        return {"type": "object"}

    if isinstance(schema, selector.SelectSelector):
        options = [
            x["value"] if isinstance(x, dict) else x for x in schema.config["options"]
        ]
        if schema.config.get("multiple"):
            return {
                "type": "array",
                "items": {"type": "string", "enum": options},
                "uniqueItems": True,
            }
        return {"type": "string", "enum": options}

    if isinstance(schema, selector.TargetSelector):
        return convert(cv.TARGET_SERVICE_FIELDS)

    if isinstance(schema, selector.TemplateSelector):
        return {"type": "string", "format": "jinja2"}

    if isinstance(schema, selector.TimeSelector):
        return {"type": "string", "format": "time"}

    if isinstance(schema, selector.TriggerSelector):
        return convert(cv.TRIGGER_SCHEMA)

    if schema.config.get("multiple"):
        return {"type": "array", "items": {"type": "string"}}

    return {"type": "string"}


class ScriptTool(Tool):
    """LLM Tool representing a Script."""

    def __init__(
        self,
        hass: HomeAssistant,
        script_state: State,
    ) -> None:
        """Init the class."""
        entity_registry = er.async_get(hass)

        self.name = split_entity_id(script_state.entity_id)[1]
        schema: dict[vol.Marker, Any] = {}
        entity_entry = entity_registry.async_get(script_state.entity_id)
        if (
            entity_entry
            and entity_entry.unique_id
            and (
                service_desc := service.async_get_cached_service_description(
                    hass, SCRIPT_DOMAIN, entity_entry.unique_id
                )
            )
        ):
            self.description = service_desc.get("description")
            fields = service_desc.get("fields", {})

            for field, config in fields.items():
                description = config.get("description")
                if not description:
                    description = config.get("name")
                if config.get("required"):
                    key = vol.Required(field, description=description)
                else:
                    key = vol.Optional(field, description=description)
                if "selector" in config:
                    schema[key] = selector.selector(config["selector"])
                else:
                    schema[key] = cv.string

        self.parameters = vol.Schema(schema)

        if not self.description:
            self.description = script_state.attributes.get("friendly_name")

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Run the script."""

        await hass.services.async_call(
            SCRIPT_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: SCRIPT_DOMAIN + "." + self.name,
                ATTR_VARIABLES: tool_input.tool_args,
            },
            context=llm_context.context,
        )

        return {"success": True}
