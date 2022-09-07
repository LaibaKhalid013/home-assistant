"""Volume conversion util functions."""
from __future__ import annotations

from numbers import Number

from homeassistant.const import (
    UNIT_NOT_RECOGNIZED_TEMPLATE,
    VOLUME,
    VOLUME_CUBIC_FEET,
    VOLUME_CUBIC_METERS,
    VOLUME_FLUID_OUNCE,
    VOLUME_GALLONS,
    VOLUME_LITERS,
    VOLUME_MILLILITERS,
)

from .distance import FOOT_TO_M

VALID_UNITS: tuple[str, ...] = (
    VOLUME_LITERS,
    VOLUME_MILLILITERS,
    VOLUME_GALLONS,
    VOLUME_FLUID_OUNCE,
    VOLUME_CUBIC_METERS,
    VOLUME_CUBIC_FEET,
)

CUBIC_FOOT_TO_CUBIC_M = pow(FOOT_TO_M, 3)
GALLON_TO_L = 3.785


def liter_to_gallon(liter: float) -> float:
    """Convert a volume measurement in Liter to Gallon."""
    return liter / GALLON_TO_L


def gallon_to_liter(gallon: float) -> float:
    """Convert a volume measurement in Gallon to Liter."""
    return gallon * GALLON_TO_L


def cubic_meter_to_cubic_feet(cubic_meter: float) -> float:
    """Convert a volume measurement in cubic meter to cubic feet."""
    return cubic_meter / CUBIC_FOOT_TO_CUBIC_M


def cubic_feet_to_cubic_meter(cubic_feet: float) -> float:
    """Convert a volume measurement in cubic feet to cubic meter."""
    return cubic_feet * CUBIC_FOOT_TO_CUBIC_M


def convert(volume: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature from one unit to another."""
    if from_unit not in VALID_UNITS:
        raise ValueError(UNIT_NOT_RECOGNIZED_TEMPLATE.format(from_unit, VOLUME))
    if to_unit not in VALID_UNITS:
        raise ValueError(UNIT_NOT_RECOGNIZED_TEMPLATE.format(to_unit, VOLUME))

    if not isinstance(volume, Number):
        raise TypeError(f"{volume} is not of numeric type")

    if from_unit == to_unit:
        return volume

    result: float = volume
    if from_unit == VOLUME_LITERS and to_unit == VOLUME_GALLONS:
        result = liter_to_gallon(volume)
    elif from_unit == VOLUME_GALLONS and to_unit == VOLUME_LITERS:
        result = gallon_to_liter(volume)
    elif from_unit == VOLUME_CUBIC_METERS and to_unit == VOLUME_CUBIC_FEET:
        result = cubic_meter_to_cubic_feet(volume)
    elif from_unit == VOLUME_CUBIC_FEET and to_unit == VOLUME_CUBIC_METERS:
        result = cubic_feet_to_cubic_meter(volume)

    return result
