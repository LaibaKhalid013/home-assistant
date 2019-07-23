"""Temperature helpers for Home Assistant."""
from numbers import Number
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.util.temperature import convert as convert_temperature
from homeassistant.const import PRECISION_HALVES, PRECISION_TENTHS


def display_temp(hass: HomeAssistant, temperature: Optional[float], unit: str,
                 precision: float) -> Optional[float]:
    """Convert temperature into preferred units/precision for display."""
    temperature_unit = unit
    ha_unit = hass.config.units.temperature_unit

    if temperature is None:
        return temperature

    # If the temperature is not a number this can cause issues
    # with Polymer components, so bail early there.
    if not isinstance(temperature, Number):
        raise TypeError(
            "Temperature is not a number: {}".format(temperature))

    # type ignore: https://github.com/python/mypy/issues/7207
    if temperature_unit != ha_unit:  # type: ignore
        temperature = convert_temperature(
            temperature, temperature_unit, ha_unit)

    # Round in the units appropriate
    if precision == PRECISION_HALVES:
        temperature = round(temperature * 2) / 2.0
    elif precision == PRECISION_TENTHS:
        temperature = round(temperature, 1)
    # Integer as a fall back (PRECISION_WHOLE)
    else:
        temperature = round(temperature)

    return temperature
