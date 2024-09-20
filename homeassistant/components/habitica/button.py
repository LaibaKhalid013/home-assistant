"""Habitica button platform."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import Any

from aiohttp import ClientResponseError

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HabiticaConfigEntry
from .const import DOMAIN, HEALER, MAGE, ROGUE, WARRIOR
from .coordinator import HabiticaData, HabiticaDataUpdateCoordinator
from .entity import HabiticaBase


@dataclass(kw_only=True, frozen=True)
class HabiticaButtonEntityDescription(ButtonEntityDescription):
    """Describes Habitica button entity."""

    press_fn: Callable[[HabiticaDataUpdateCoordinator], Any]
    available_fn: Callable[[HabiticaData], bool] | None = None


class HabitipyButtonEntity(StrEnum):
    """Habitica button entities."""

    RUN_CRON = "run_cron"
    BUY_HEALTH_POTION = "buy_health_potion"
    ALLOCATE_ALL_STAT_POINTS = "allocate_all_stat_points"
    REVIVE = "revive"
    MPHEAL = "mpheal"
    EARTH = "earth"
    FROST = "frost"
    DEFENSIVE_STANCE = "defensive_stance"
    VALOROUS_PRESENCE = "valorous_presence"
    INTIMIDATE = "intimidate"
    TOOLS_OF_TRADE = "tools_of_trade"
    STEALTH = "stealth"
    HEAL = "heal"
    PROTECT_AURA = "protect_aura"
    BRIGHTNESS = "brightness"
    HEAL_ALL = "heal_all"


BUTTON_DESCRIPTIONS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.RUN_CRON,
        translation_key=HabitipyButtonEntity.RUN_CRON,
        press_fn=lambda coordinator: coordinator.api.cron.post(),
        available_fn=lambda data: data.user["needsCron"],
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.BUY_HEALTH_POTION,
        translation_key=HabitipyButtonEntity.BUY_HEALTH_POTION,
        press_fn=(
            lambda coordinator: coordinator.api["user"]["buy-health-potion"].post()
        ),
        available_fn=(
            lambda data: data.user["stats"]["gp"] >= 25
            and data.user["stats"]["hp"] < 50
        ),
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.ALLOCATE_ALL_STAT_POINTS,
        translation_key=HabitipyButtonEntity.ALLOCATE_ALL_STAT_POINTS,
        press_fn=lambda coordinator: coordinator.api["user"]["allocate-now"].post(),
        available_fn=(
            lambda data: data.user["preferences"].get("automaticAllocation") is True
            and data.user["stats"]["points"] > 0
        ),
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.REVIVE,
        translation_key=HabitipyButtonEntity.REVIVE,
        press_fn=lambda coordinator: coordinator.api["user"]["revive"].post(),
        available_fn=lambda data: data.user["stats"]["hp"] == 0,
    ),
)


MAGE_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.MPHEAL,
        translation_key=HabitipyButtonEntity.MPHEAL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["mpheal"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12
        and data.user["stats"]["mp"] >= 30
        and data.user["stats"]["class"] == MAGE,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.EARTH,
        translation_key=HabitipyButtonEntity.EARTH,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["earth"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13
        and data.user["stats"]["mp"] >= 35
        and data.user["stats"]["class"] == MAGE,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.FROST,
        translation_key=HabitipyButtonEntity.FROST,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["frost"].post(
            targetId=coordinator.config_entry.unique_id
        ),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14
        and data.user["stats"]["mp"] >= 40
        and data.user["stats"]["class"] == MAGE,
    ),
)

WARRIOR_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.DEFENSIVE_STANCE,
        translation_key=HabitipyButtonEntity.DEFENSIVE_STANCE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "defensiveStance"
        ].post(targetId=coordinator.config_entry.unique_id),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12
        and data.user["stats"]["mp"] >= 25
        and data.user["stats"]["class"] == WARRIOR,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.VALOROUS_PRESENCE,
        translation_key=HabitipyButtonEntity.VALOROUS_PRESENCE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "valorousPresence"
        ].post(targetId=coordinator.config_entry.unique_id),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13
        and data.user["stats"]["mp"] >= 20
        and data.user["stats"]["class"] == WARRIOR,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.INTIMIDATE,
        translation_key=HabitipyButtonEntity.INTIMIDATE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "intimidate"
        ].post(targetId=coordinator.config_entry.unique_id),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14
        and data.user["stats"]["mp"] >= 15
        and data.user["stats"]["class"] == WARRIOR,
    ),
)

ROGUE_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.TOOLS_OF_TRADE,
        translation_key=HabitipyButtonEntity.TOOLS_OF_TRADE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "toolsOfTrade"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13
        and data.user["stats"]["mp"] >= 25
        and data.user["stats"]["class"] == ROGUE,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.STEALTH,
        translation_key=HabitipyButtonEntity.STEALTH,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["stealth"].post(
            targetId=coordinator.config_entry.unique_id
        ),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14
        and data.user["stats"]["mp"] >= 45
        and data.user["stats"]["class"] == ROGUE,
    ),
)

HEALER_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.HEAL,
        translation_key=HabitipyButtonEntity.HEAL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["heal"].post(
            targetId=coordinator.config_entry.unique_id
        ),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 11
        and data.user["stats"]["mp"] >= 15
        and data.user["stats"]["class"] == HEALER,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.BRIGHTNESS,
        translation_key=HabitipyButtonEntity.BRIGHTNESS,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "brightness"
        ].post(targetId=coordinator.config_entry.unique_id),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12
        and data.user["stats"]["mp"] >= 15
        and data.user["stats"]["class"] == HEALER,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.PROTECT_AURA,
        translation_key=HabitipyButtonEntity.PROTECT_AURA,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "protectAura"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13
        and data.user["stats"]["mp"] >= 30
        and data.user["stats"]["class"] == HEALER,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.HEAL_ALL,
        translation_key=HabitipyButtonEntity.HEAL_ALL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["healAll"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14
        and data.user["stats"]["mp"] >= 25
        and data.user["stats"]["class"] == HEALER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HabiticaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons from a config entry."""

    coordinator = entry.runtime_data

    async_add_entities(
        HabiticaButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )
    if coordinator.data.user["stats"]["lvl"] >= 10:
        if coordinator.data.user["stats"]["class"] == MAGE:
            async_add_entities(
                HabiticaButton(coordinator, description) for description in MAGE_SKILLS
            )
        if coordinator.data.user["stats"]["class"] == WARRIOR:
            async_add_entities(
                HabiticaButton(coordinator, description)
                for description in WARRIOR_SKILLS
            )
        if coordinator.data.user["stats"]["class"] == ROGUE:
            async_add_entities(
                HabiticaButton(coordinator, description) for description in ROGUE_SKILLS
            )
        if coordinator.data.user["stats"]["class"] == HEALER:
            async_add_entities(
                HabiticaButton(coordinator, description)
                for description in HEALER_SKILLS
            )


class HabiticaButton(HabiticaBase, ButtonEntity):
    """Representation of a Habitica button."""

    entity_description: HabiticaButtonEntityDescription

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.entity_description.press_fn(self.coordinator)
        except ClientResponseError as e:
            if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="setup_rate_limit_exception",
                ) from e
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="service_call_unallowed",
                ) from e
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
            ) from e
        else:
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Is entity available."""
        if not super().available:
            return False
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(self.coordinator.data)
        return True
