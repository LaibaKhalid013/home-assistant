"""The habitica integration."""

from http import HTTPStatus
import logging
from typing import Any

from aiohttp import ClientResponseError
from habitipy.aio import HabitipyAsync
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    CONF_API_KEY,
    CONF_NAME,
    CONF_SENSORS,
    CONF_URL,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import ConfigEntrySelector
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ARGS,
    ATTR_CONFIG_ENTRY,
    ATTR_DATA,
    ATTR_PATH,
    ATTR_SKILL,
    ATTR_TASK,
    CONF_API_USER,
    DEFAULT_URL,
    DOMAIN,
    EVENT_API_CALL_SUCCESS,
    SERVICE_API_CALL,
    SERVICE_CAST_SKILL,
)
from .coordinator import HabiticaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

type HabiticaConfigEntry = ConfigEntry[HabiticaDataUpdateCoordinator]

SENSORS_TYPES = ["name", "hp", "maxHealth", "mp", "maxMP", "exp", "toNextLevel", "lvl"]

INSTANCE_SCHEMA = vol.All(
    cv.deprecated(CONF_SENSORS),
    vol.Schema(
        {
            vol.Optional(CONF_URL, default=DEFAULT_URL): cv.url,
            vol.Optional(CONF_NAME): cv.string,
            vol.Required(CONF_API_USER): cv.string,
            vol.Required(CONF_API_KEY): cv.string,
            vol.Optional(CONF_SENSORS, default=list(SENSORS_TYPES)): vol.All(
                cv.ensure_list, vol.Unique(), [vol.In(list(SENSORS_TYPES))]
            ),
        }
    ),
)

has_unique_values = vol.Schema(vol.Unique())
# because we want a handy alias


def has_all_unique_users(value):
    """Validate that all API users are unique."""
    api_users = [user[CONF_API_USER] for user in value]
    has_unique_values(api_users)
    return value


def has_all_unique_users_names(value):
    """Validate that all user's names are unique and set if any is set."""
    names = [user.get(CONF_NAME) for user in value]
    if None in names and any(name is not None for name in names):
        raise vol.Invalid("user names of all users must be set if any is set")
    if not all(name is None for name in names):
        has_unique_values(names)
    return value


INSTANCE_LIST_SCHEMA = vol.All(
    cv.ensure_list, has_all_unique_users, has_all_unique_users_names, [INSTANCE_SCHEMA]
)
CONFIG_SCHEMA = vol.Schema({DOMAIN: INSTANCE_LIST_SCHEMA}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH, Platform.TODO]

SERVICE_API_CALL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): str,
        vol.Required(ATTR_PATH): vol.All(cv.ensure_list, [str]),
        vol.Optional(ATTR_ARGS): dict,
    }
)
SERVICE_CAST_SKILL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY): ConfigEntrySelector(),
        vol.Required(ATTR_SKILL): cv.string,
        vol.Optional(ATTR_TASK): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Habitica service."""
    configs = config.get(DOMAIN, [])

    for conf in configs:
        if conf.get(CONF_URL) is None:
            conf[CONF_URL] = DEFAULT_URL

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )

    async def cast_skill(call: ServiceCall) -> ServiceResponse:
        """Skill action."""
        entry: HabiticaConfigEntry | None
        if not (
            entry := hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY])
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_found",
            )
        coordinator = entry.runtime_data
        skill = {
            "pickpocket": {"spellId": "pickPocket", "cost": "10 MP"},
            "backstab": {"spellId": "backStab", "cost": "15 MP"},
            "smash": {"spellId": "smash", "cost": "10 MP"},
            "fireball": {"spellId": "fireball", "cost": "10 MP"},
        }
        try:
            task_id = next(
                task["id"]
                for task in coordinator.data.tasks
                if call.data[ATTR_TASK] in (task["id"], task.get("alias"))
                or call.data[ATTR_TASK] == task["text"]
            )
        except StopIteration as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="task_not_found",
                translation_placeholders={"task": f"'{call.data[ATTR_TASK]}'"},
            ) from e

        try:
            response: dict[str, Any] = await coordinator.api.user.class_.cast[
                skill[call.data[ATTR_SKILL]]["spellId"]
            ].post(targetId=task_id)
        except ClientResponseError as e:
            if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="setup_rate_limit_exception",
                ) from e
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="not_enough_mana",
                    translation_placeholders={
                        "cost": skill[call.data[ATTR_SKILL]]["cost"],
                        "mana": f"{int(coordinator.data.user.get("stats", {}).get("mp", 0))} MP",
                    },
                ) from e
            if e.status == HTTPStatus.NOT_FOUND:
                # could also be task not found, but the task is looked up
                # before the request, so most likely wrong skill selected
                # or the skill hasn't been unlocked yet.
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="skill_not_found",
                    translation_placeholders={"skill": call.data[ATTR_SKILL]},
                ) from e
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
            ) from e
        else:
            await coordinator.async_request_refresh()
            return response

    hass.services.async_register(
        DOMAIN,
        SERVICE_CAST_SKILL,
        cast_skill,
        schema=SERVICE_CAST_SKILL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: HabiticaConfigEntry
) -> bool:
    """Set up habitica from a config entry."""

    class HAHabitipyAsync(HabitipyAsync):
        """Closure API class to hold session."""

        def __call__(self, **kwargs):
            return super().__call__(websession, **kwargs)

    async def handle_api_call(call: ServiceCall) -> None:
        name = call.data[ATTR_NAME]
        path = call.data[ATTR_PATH]
        entries = hass.config_entries.async_entries(DOMAIN)

        api = None
        for entry in entries:
            if entry.data[CONF_NAME] == name:
                api = entry.runtime_data.api
                break
        if api is None:
            _LOGGER.error("API_CALL: User '%s' not configured", name)
            return
        try:
            for element in path:
                api = api[element]
        except KeyError:
            _LOGGER.error(
                "API_CALL: Path %s is invalid for API on '{%s}' element", path, element
            )
            return
        kwargs = call.data.get(ATTR_ARGS, {})
        data = await api(**kwargs)
        hass.bus.async_fire(
            EVENT_API_CALL_SUCCESS, {ATTR_NAME: name, ATTR_PATH: path, ATTR_DATA: data}
        )

    websession = async_get_clientsession(
        hass, verify_ssl=config_entry.data.get(CONF_VERIFY_SSL, True)
    )

    api = await hass.async_add_executor_job(
        HAHabitipyAsync,
        {
            "url": config_entry.data[CONF_URL],
            "login": config_entry.data[CONF_API_USER],
            "password": config_entry.data[CONF_API_KEY],
        },
    )
    try:
        user = await api.user.get(userFields="profile")
    except ClientResponseError as e:
        if e.status == HTTPStatus.TOO_MANY_REQUESTS:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="setup_rate_limit_exception",
            ) from e
        raise ConfigEntryNotReady(e) from e

    if not config_entry.data.get(CONF_NAME):
        name = user["profile"]["name"]
        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data, CONF_NAME: name},
        )

    coordinator = HabiticaDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_API_CALL):
        hass.services.async_register(
            DOMAIN, SERVICE_API_CALL, handle_api_call, schema=SERVICE_API_CALL_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        hass.services.async_remove(DOMAIN, SERVICE_API_CALL)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
